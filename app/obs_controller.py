import threading
import time
from typing import Callable, Optional, List, Tuple

try:
    import obsws_python as obsws
    OBSWS_AVAILABLE = True
except ImportError:
    OBSWS_AVAILABLE = False


class OBSController:
    """
    Controlador para o OBS Studio via OBS WebSocket 5.x.
    Suporta conexão, verificação de cena, troca de cena e reconexão automática.
    """
    def __init__(self, host: str = "localhost", port: int = 4455, password: str = ""):
        self.host = host
        self.port = port
        self.password = password

        self.client = None
        self.connected = False
        self._lock = threading.Lock()

        # Thread de auto-reconexão
        self._auto_reconnect_running = False
        self._reconnect_thread = None

        # Callbacks de alteração de status
        self.on_status_change: Optional[Callable[[bool, str], None]] = None

    def update_credentials(self, host: str, port: int, password: str):
        """Atualiza credenciais e desconecta para forçar nova reconexão se necessário."""
        with self._lock:
            self.host = host
            self.port = port
            self.password = password
        if self.connected:
            self.disconnect()

    def connect(self) -> Tuple[bool, str]:
        """Tenta estabelecer conexão com o OBS WebSocket 5.x."""
        if not OBSWS_AVAILABLE:
            msg = "Biblioteca obsws-python não instalada."
            self._set_status(False, msg)
            return False, msg

        with self._lock:
            if self.connected and self.client is not None:
                return True, "Já conectado ao OBS."

            try:
                print(f"[OBS] Conectando a {self.host}:{self.port}...")
                self.client = obsws.ReqClient(
                    host=self.host,
                    port=self.port,
                    password=self.password,
                    timeout=3
                )
                
                # Testar resposta obtendo lista de cenas
                res = self.client.get_scene_list()
                self.connected = True
                msg = f"Conectado ao OBS Studio ({len(res.scenes)} cenas encontradas)."
                print(f"[OBS] {msg}")
                self._set_status(True, msg)
                return True, msg

            except Exception as e:
                self.client = None
                self.connected = False
                err_msg = self._format_error_message(e)
                print(f"[OBS] Falha de conexão: {err_msg}")
                self._set_status(False, err_msg)
                return False, err_msg

    def disconnect(self):
        """Desconecta do OBS de forma limpa."""
        with self._lock:
            if self.client:
                try:
                    self.client.disconnect()
                except Exception:
                    pass
            self.client = None
            self.connected = False
        self._set_status(False, "Desconectado do OBS Studio.")

    def is_connected(self) -> bool:
        """Verifica se a conexão está ativa no momento."""
        with self._lock:
            return self.connected and self.client is not None

    def change_scene(self, scene_name: str) -> Tuple[bool, str]:
        """
        Troca a cena atual do OBS para a cena especificada.
        Retorna (sucesso: bool, mensagem_explicativa: str).
        """
        if not self.is_connected():
            return False, "OBS não está conectado. Clique em 'Conectar ao OBS'."

        with self._lock:
            try:
                # 1. Verifica se a cena realmente existe na lista de cenas do OBS
                scenes_res = self.client.get_scene_list()
                available_scenes = []
                if hasattr(scenes_res, 'scenes'):
                    # Pega os nomes das cenas
                    for s in scenes_res.scenes:
                        if isinstance(s, dict):
                            available_scenes.append(s.get('sceneName'))
                        elif hasattr(s, 'sceneName'):
                            available_scenes.append(s.sceneName)
                        elif isinstance(s, str):
                            available_scenes.append(s)

                if available_scenes and scene_name not in available_scenes:
                    msg = (f"A cena '{scene_name}' não existe no OBS Studio!\n"
                           f"Cenas disponíveis: {', '.join(str(s) for s in available_scenes)}")
                    print(f"[OBS] {msg}")
                    return False, msg

                # 2. Executa a troca de cena via API v5 (SetCurrentProgramScene)
                self.client.set_current_program_scene(scene_name)
                msg = f"Cena alterada para '{scene_name}'"
                print(f"[OBS] {msg}")
                return True, msg

            except Exception as e:
                err_msg = self._format_error_message(e)
                # Se for erro de socket ou conexão perdida, atualiza o status
                if "connection" in err_msg.lower() or "socket" in err_msg.lower() or "timeout" in err_msg.lower():
                    self.connected = False
                    self.client = None
                    self._set_status(False, "Conexão perdida com o OBS.")
                return False, f"Erro ao trocar cena para '{scene_name}': {err_msg}"

    def start_auto_reconnect(self, interval: float = 5.0):
        """Inicia thread de verificação e reconexão automática."""
        if self._auto_reconnect_running:
            return

        self._auto_reconnect_running = True

        def reconnect_loop():
            while self._auto_reconnect_running:
                time.sleep(interval)
                if not self.is_connected() and self._auto_reconnect_running:
                    print("[OBS] Tentando reconectar automaticamente ao OBS WebSocket...")
                    self.connect()

        self._reconnect_thread = threading.Thread(target=reconnect_loop, daemon=True)
        self._reconnect_thread.start()

    def stop_auto_reconnect(self):
        """Para a thread de auto-reconexão."""
        self._auto_reconnect_running = False

    def _set_status(self, connected: bool, message: str):
        """Notifica o listener/interface sobre mudanças de estado da conexão."""
        if self.on_status_change:
            try:
                self.on_status_change(connected, message)
            except Exception as e:
                print(f"[OBS] Erro ao chamar callback de status: {e}")

    def _format_error_message(self, error: Exception) -> str:
        """Formata erros de conexão em mensagens amigáveis."""
        err_str = str(error)
        if "Connection refused" in err_str or "WinError 10061" in err_str:
            return "Conexão recusada. O OBS Studio está aberto com o servidor WebSocket ativo na porta 4455?"
        if "Authentication failed" in err_str or "auth" in err_str.lower():
            return "Senha incorreta do OBS WebSocket. Verifique nas Configurações."
        if "timeout" in err_str.lower():
            return "Tempo limite esgotado ao tentar conectar ao OBS."
        return f"Erro OBS WebSocket: {err_str}"
