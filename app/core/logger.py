import time
import threading
from typing import List, Callable, Optional
from app.core.events import event_bus

class AppLogger:
    """
    Gerenciador de logs centralizado com buffer em memória e notificação em tempo real para a GUI.
    """
    _instance = None
    _lock = threading.RLock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(AppLogger, cls).__new__(cls)
                cls._instance.logs: List[str] = []
                cls._instance.max_logs = 500
            return cls._instance

    def log(self, message: str, level: str = "INFO"):
        timestamp = time.strftime("%H:%M:%S")
        formatted = f"[{timestamp}] [{level}] {message}"
        print(formatted)
        
        with self._lock:
            self.logs.append(formatted)
            if len(self.logs) > self.max_logs:
                self.logs.pop(0)

        event_bus.publish("on_log_message", log_text=formatted, level=level, timestamp=timestamp, message=message)

    def get_logs(self) -> List[str]:
        with self._lock:
            return list(self.logs)

    def clear(self):
        with self._lock:
            self.logs.clear()
        event_bus.publish("on_log_message", log_text="[System] Logs limpos.", level="INFO", timestamp=time.strftime("%H:%M:%S"), message="Logs limpos")

logger = AppLogger()
