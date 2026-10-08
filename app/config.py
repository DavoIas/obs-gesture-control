import json
import os
import threading
from typing import Dict, Any

class ConfigManager:
    """
    Gerenciador de configurações em arquivo JSON.
    Garante leitura/escrita de forma segura e mantém valores padrão.
    """
    DEFAULT_CONFIG: Dict[str, Any] = {
        "obs": {
            "host": "localhost",
            "port": 4455,
            "password": ""
        },
        "gestures": {
            "peace": {
                "enabled": True,
                "scene": "Cena 2",
                "cooldown": 1.5
            },
            "three": {
                "enabled": True,
                "scene": "Cena 1",
                "cooldown": 1.5
            }
        },
        "camera": {
            "device_index": 0,
            "width": 640,
            "height": 480
        }
    }

    def __init__(self, config_path: str = "config.json"):
        self.config_path = config_path
        self._lock = threading.Lock()
        self.config = self.load_config()

    def load_config(self) -> Dict[str, Any]:
        """Carrega a configuração do arquivo JSON ou retorna o padrão se falhar."""
        with self._lock:
            if not os.path.exists(self.config_path):
                self.save_config(self.DEFAULT_CONFIG)
                return self.DEFAULT_CONFIG.copy()

            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                # Garante que chaves faltantes do padrão existam no dicionário carregado
                merged = self._merge_defaults(data, self.DEFAULT_CONFIG)
                return merged
            except Exception as e:
                print(f"[Config] Erro ao carregar {self.config_path}: {e}. Usando configuração padrão.")
                return self.DEFAULT_CONFIG.copy()

    def save_config(self, new_config: Dict[str, Any] = None) -> bool:
        """Salva a configuração atual ou uma nova no arquivo config.json."""
        with self._lock:
            if new_config is not None:
                self.config = new_config

            try:
                with open(self.config_path, "w", encoding="utf-8") as f:
                    json.dump(self.config, f, indent=2, ensure_ascii=False)
                return True
            except Exception as e:
                print(f"[Config] Erro ao salvar configurações: {e}")
                return False

    def _merge_defaults(self, data: Dict[str, Any], default: Dict[str, Any]) -> Dict[str, Any]:
        """Mescla chaves ausentes com base na estrutura default."""
        merged = default.copy()
        for key, val in data.items():
            if isinstance(val, dict) and key in merged and isinstance(merged[key], dict):
                merged[key] = self._merge_defaults(val, merged[key])
            else:
                merged[key] = val
        return merged

    def get_obs_config(self) -> Dict[str, Any]:
        return self.config.get("obs", self.DEFAULT_CONFIG["obs"])

    def get_gesture_config(self, gesture_name: str) -> Dict[str, Any]:
        gestures = self.config.get("gestures", {})
        default_scene = "Cena 1" if gesture_name == "three" else "Cena 2"
        return gestures.get(gesture_name, {"enabled": True, "scene": default_scene, "cooldown": 1.5})

    def get_camera_config(self) -> Dict[str, Any]:
        return self.config.get("camera", self.DEFAULT_CONFIG["camera"])

    def update_settings(self, obs_host: str, obs_port: int, obs_password: str,
                        peace_scene: str, cooldown: float, camera_index: int,
                        three_scene: str = "Cena 1") -> bool:
        """Atualiza e salva as configurações principais de forma simplificada."""
        self.config["obs"]["host"] = obs_host
        self.config["obs"]["port"] = obs_port
        self.config["obs"]["password"] = obs_password
        
        if "gestures" not in self.config:
            self.config["gestures"] = {}
        if "peace" not in self.config["gestures"]:
            self.config["gestures"]["peace"] = {}
        if "three" not in self.config["gestures"]:
            self.config["gestures"]["three"] = {}

        self.config["gestures"]["peace"]["scene"] = peace_scene
        self.config["gestures"]["peace"]["cooldown"] = cooldown
        self.config["gestures"]["three"]["scene"] = three_scene
        self.config["gestures"]["three"]["cooldown"] = cooldown
        
        if "camera" not in self.config:
            self.config["camera"] = {}
        self.config["camera"]["device_index"] = camera_index

        return self.save_config()
