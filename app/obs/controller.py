import time
import threading
from typing import Optional, List, Dict, Any
import obsws_python as obs
from app.config.manager import config_manager
from app.core.logger import logger
from app.core.events import event_bus

class OBSController:
    """
    Gerenciador da conexão WebSocket 5.x com o OBS Studio.
    Oferece reconexão automática, resiliência a falhas e controle de estado.
    """
    _instance = None
    _lock = threading.RLock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(OBSController, cls).__new__(cls)
                cls._instance.client: Optional[obs.ReqClient] = None
                cls._instance.is_connected = False
                cls._instance._reconnect_thread = None
                cls._instance._stop_reconnect = False
            return cls._instance

    def connect(self) -> bool:
        with self._lock:
            if self.is_connected and self.client:
                return True

            cfg = config_manager.config.obs
            logger.log(f"Tentando conectar ao OBS WebSocket em {cfg.host}:{cfg.port}...")
            try:
                self.client = obs.ReqClient(
                    host=cfg.host,
                    port=cfg.port,
                    password=cfg.password,
                    timeout=3
                )
                self.is_connected = True
                logger.log("Conectado com sucesso ao OBS Studio!", "INFO")
                event_bus.publish("on_obs_status", connected=True, message="Conectado ao OBS Studio")
                return True
            except Exception as e:
                self.is_connected = False
                self.client = None
                err_msg = f"Falha na conexão com OBS ({cfg.host}:{cfg.port}): {e}"
                logger.log(err_msg, "WARNING")
                event_bus.publish("on_obs_status", connected=False, message=err_msg)

                if cfg.auto_reconnect and not self._reconnect_thread:
                    self._start_auto_reconnect()
                return False

    def disconnect(self):
        with self._lock:
            self._stop_reconnect = True
            if self.client:
                try:
                    self.client.disconnect()
                except Exception:
                    pass
                self.client = None
            self.is_connected = False
            logger.log("Desconectado do OBS Studio.")
            event_bus.publish("on_obs_status", connected=False, message="Desconectado")

    def _start_auto_reconnect(self):
        self._stop_reconnect = False
        def reconnect_loop():
            while not self._stop_reconnect and not self.is_connected:
                cfg = config_manager.config.obs
                time.sleep(cfg.reconnect_interval)
                if self._stop_reconnect or self.is_connected:
                    break
                logger.log("Tentando reconexão automática com OBS...", "INFO")
                if self.connect():
                    break
            self._reconnect_thread = None

        self._reconnect_thread = threading.Thread(target=reconnect_loop, daemon=True)
        self._reconnect_thread.start()

    def get_client(self) -> Optional[obs.ReqClient]:
        return self.client

obs_controller = OBSController()
