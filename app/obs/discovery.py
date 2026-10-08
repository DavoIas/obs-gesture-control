import threading
from typing import List, Dict, Any
from app.obs.controller import obs_controller
from app.core.logger import logger
from app.core.events import event_bus

class OBSDiscovery:
    """
    Descobre automaticamente cenas, fontes e dispositivos de áudio disponíveis no OBS Studio.
    Mantém os dados atualizados para preencher os menus dropdowns da GUI.
    """
    _instance = None
    _lock = threading.RLock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(OBSDiscovery, cls).__new__(cls)
                cls._instance.scenes: List[str] = []
                cls._instance.sources: List[str] = []
                cls._instance.scene_sources: Dict[str, List[str]] = {}
            return cls._instance

    def refresh(self) -> bool:
        client = obs_controller.get_client()
        if not client or not obs_controller.is_connected:
            return False

        try:
            # Buscar cenas
            scenes_resp = client.get_scene_list()
            scenes_list = []
            if hasattr(scenes_resp, 'scenes'):
                for s in scenes_resp.scenes:
                    name = s.get('sceneName', '') if isinstance(s, dict) else getattr(s, 'scene_name', str(s))
                    if name:
                        scenes_list.append(name)
            self.scenes = scenes_list if scenes_list else ["Gameplay", "Just Chatting", "BRB", "Starting Soon"]

            # Buscar fontes / entradas
            inputs_resp = client.get_input_list()
            sources_list = []
            if hasattr(inputs_resp, 'inputs'):
                for inp in inputs_resp.inputs:
                    name = inp.get('inputName', '') if isinstance(inp, dict) else getattr(inp, 'input_name', str(inp))
                    if name:
                        sources_list.append(name)
            self.sources = sources_list if sources_list else ["Webcam", "Mic/Aux", "Alertas", "Chat", "Música"]

            logger.log(f"Descoberta do OBS concluída: {len(self.scenes)} cenas e {len(self.sources)} fontes encontradas.")
            event_bus.publish("on_obs_discovery_refreshed", scenes=self.scenes, sources=self.sources)
            return True
        except Exception as e:
            logger.log(f"Erro ao descobrir cenas/fontes no OBS: {e}", "WARNING")
            return False

    def get_scenes(self) -> List[str]:
        if not self.scenes:
            self.refresh()
        return self.scenes if self.scenes else ["Gameplay", "Just Chatting", "BRB", "Starting Soon"]

    def get_sources(self) -> List[str]:
        if not self.sources:
            self.refresh()
        return self.sources if self.sources else ["Webcam", "Mic/Aux", "Alertas", "Chat", "Música"]

obs_discovery = OBSDiscovery()
