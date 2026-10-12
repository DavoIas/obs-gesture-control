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
            with self._lock:
                self.scenes = []
                self.sources = []
                self.scene_sources = {}
            event_bus.publish("on_obs_discovery_refreshed", scenes=[], sources=[])
            return False

        try:
            # 1. Buscar cenas reais
            scenes_resp = client.get_scene_list()
            scenes_list = []
            if hasattr(scenes_resp, 'scenes'):
                for s in scenes_resp.scenes:
                    name = s.get('sceneName', '') if isinstance(s, dict) else getattr(s, 'scene_name', str(s))
                    if name:
                        scenes_list.append(name)

            # 2. Buscar fontes / entradas reais de áudio e vídeo
            inputs_resp = client.get_input_list()
            sources_list = []
            if hasattr(inputs_resp, 'inputs'):
                for inp in inputs_resp.inputs:
                    name = inp.get('inputName', '') if isinstance(inp, dict) else getattr(inp, 'input_name', str(inp))
                    if name:
                        sources_list.append(name)

            # 3. Preencher scene_sources com get_scene_item_list por cena (T6)
            scene_sources_map: Dict[str, List[str]] = {}
            for sc in scenes_list:
                try:
                    items_resp = client.get_scene_item_list(sc)
                    items = getattr(items_resp, 'scene_items', []) or []
                    items_names = []
                    for item in items:
                        src_name = item.get('sourceName', '') if isinstance(item, dict) else getattr(item, 'source_name', '')
                        if src_name and src_name not in items_names:
                            items_names.append(src_name)
                    scene_sources_map[sc] = items_names
                except Exception:
                    scene_sources_map[sc] = []

            with self._lock:
                self.scenes = scenes_list
                self.sources = sources_list
                self.scene_sources = scene_sources_map

            logger.log(f"Descoberta do OBS concluída: {len(self.scenes)} cenas e {len(self.sources)} fontes encontradas.")
            event_bus.publish("on_obs_discovery_refreshed", scenes=self.scenes, sources=self.sources)
            return True
        except Exception as e:
            logger.log(f"Erro ao descobrir cenas/fontes no OBS: {e}", "WARNING")
            return False

    def get_scenes(self) -> List[str]:
        with self._lock:
            if not self.scenes and obs_controller.is_connected:
                self.refresh()
            return list(self.scenes)

    def get_sources(self) -> List[str]:
        with self._lock:
            if not self.sources and obs_controller.is_connected:
                self.refresh()
            return list(self.sources)

    def get_scene_sources(self, scene_name: str) -> List[str]:
        with self._lock:
            if not self.scene_sources and obs_controller.is_connected:
                self.refresh()
            return list(self.scene_sources.get(scene_name, []))

obs_discovery = OBSDiscovery()
