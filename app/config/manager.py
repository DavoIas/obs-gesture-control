import os
import json
import threading
from typing import Optional, List, Dict, Any
from app.config.models import AppConfig, ProfileConfig, GestureConfig, ActionConfig
from app.config.defaults import create_default_config, create_default_8_gestures
from app.core.logger import logger
from app.core.events import event_bus

CONFIG_FILE_PATH = "config.json"

class ConfigManager:
    """
    Gerenciador thread-safe de carregamento, validação, persistência e troca de perfis
    sem necessidade de alteração direta em arquivos Python pelo usuário.
    """
    _instance = None
    _lock = threading.RLock()

    def __new__(cls, config_path: str = CONFIG_FILE_PATH):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(ConfigManager, cls).__new__(cls)
                cls._instance.config_path = config_path
                cls._instance.config: AppConfig = create_default_config()
                cls._instance.load()
            return cls._instance

    def load(self) -> AppConfig:
        with self._lock:
            if not os.path.exists(self.config_path):
                logger.log(f"Arquivo de configuração '{self.config_path}' não encontrado. Criando padrão V2...")
                self.config = create_default_config()
                self._save_unlocked()
                return self.config

            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                self.config = AppConfig.from_dict(data)
                self._ensure_integrity_unlocked()
                logger.log(f"Configurações carregadas com sucesso! Perfil ativo: '{self.config.active_profile}'")
            except Exception as e:
                logger.log(f"Erro ao ler '{self.config_path}': {e}. Restaurando configuração padrão segura.", "WARNING")
                self.config = create_default_config()
                self._save_unlocked()

            return self.config

    def save(self):
        with self._lock:
            self._save_unlocked()

    def _save_unlocked(self):
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.config.to_dict(), f, indent=2, ensure_ascii=False)
            event_bus.publish("on_config_updated", config=self.config)
        except Exception as e:
            logger.log(f"Erro ao salvar configurações em '{self.config_path}': {e}", "ERROR")

    def _ensure_integrity_unlocked(self):
        """Garante que existam perfis e que todos tenham os 8 gestos obrigatórios."""
        if not self.config.profiles:
            def_cfg = create_default_config()
            self.config.profiles = def_cfg.profiles
            self.config.active_profile = def_cfg.active_profile

        if self.config.active_profile not in self.config.profiles:
            self.config.active_profile = list(self.config.profiles.keys())[0]

        default_8 = create_default_8_gestures()
        for p_name, profile in self.config.profiles.items():
            for g_id, g_default in default_8.items():
                if g_id not in profile.gestures:
                    profile.gestures[g_id] = g_default

    def get_active_profile(self) -> ProfileConfig:
        with self._lock:
            if self.config.active_profile not in self.config.profiles:
                self.config.active_profile = list(self.config.profiles.keys())[0]
            return self.config.profiles[self.config.active_profile]

    def set_active_profile(self, profile_name: str) -> bool:
        with self._lock:
            if profile_name in self.config.profiles:
                self.config.active_profile = profile_name
                self._save_unlocked()
                logger.log(f"Perfil trocado para '{profile_name}'")
                return True
            return False

    def create_profile(self, name: str, copy_from: Optional[str] = None) -> bool:
        with self._lock:
            if not name or name in self.config.profiles:
                return False

            if copy_from and copy_from in self.config.profiles:
                base_dict = self.config.profiles[copy_from].to_dict()
                base_dict["name"] = name
                new_profile = ProfileConfig.from_dict(base_dict)
            else:
                new_profile = ProfileConfig(
                    name=name,
                    description=f"Perfil personalizado: {name}",
                    gestures=create_default_8_gestures()
                )

            self.config.profiles[name] = new_profile
            self.config.active_profile = name
            self._save_unlocked()
            logger.log(f"Perfil '{name}' criado com sucesso.")
            return True

    def delete_profile(self, name: str) -> bool:
        with self._lock:
            if name in self.config.profiles and len(self.config.profiles) > 1:
                del self.config.profiles[name]
                if self.config.active_profile == name:
                    self.config.active_profile = list(self.config.profiles.keys())[0]
                self._save_unlocked()
                logger.log(f"Perfil '{name}' excluído.")
                return True
            return False

    def update_gesture(self, gesture_id: str, updated_gesture: GestureConfig):
        with self._lock:
            active_p = self.get_active_profile()
            active_p.gestures[gesture_id] = updated_gesture
            self._save_unlocked()
            logger.log(f"Gesto '{gesture_id}' atualizado no perfil '{active_p.name}'.")

    def set_test_mode(self, enabled: bool):
        with self._lock:
            self.config.test_mode = enabled
            self._save_unlocked()
            logger.log(f"Modo Teste {'ATIVADO' if enabled else 'DESATIVADO'}.")

config_manager = ConfigManager()
