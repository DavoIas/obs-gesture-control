import os
import json
import threading
import shutil
from pathlib import Path
from typing import Optional, List, Dict, Any
from app.config.models import AppConfig, ProfileConfig, GestureConfig, ActionConfig
from app.config.defaults import create_default_config, create_default_8_gestures
from app.core.logger import logger
from app.core.events import event_bus

ROOT = Path(__file__).resolve().parents[2]
LOCAL_CONFIG_PATH = ROOT / "config.json"

def get_default_config_path() -> str:
    """Retorna o caminho do config no diretório do usuário com migração automática do config local (C3)."""
    try:
        if os.name == 'nt':
            appdata = os.environ.get("APPDATA")
            base_dir = Path(appdata) if appdata else Path.home() / "AppData" / "Roaming"
            config_dir = base_dir / "obs-gesture-control"
        else:
            xdg_config = os.environ.get("XDG_CONFIG_HOME")
            base_dir = Path(xdg_config) if xdg_config else Path.home() / ".config"
            config_dir = base_dir / "obs-gesture-control"

        config_dir.mkdir(parents=True, exist_ok=True)
        user_config_path = config_dir / "config.json"

        # Migração do config.json local se existir
        if not user_config_path.exists() and LOCAL_CONFIG_PATH.exists():
            shutil.copy2(LOCAL_CONFIG_PATH, user_config_path)
            logger.log(f"Configuração local migrada de '{LOCAL_CONFIG_PATH}' para '{user_config_path}'.")

        return str(user_config_path)
    except Exception as e:
        logger.log(f"Não foi possível acessar diretório do usuário: {e}. Usando raiz do projeto.", "WARNING")
        return str(LOCAL_CONFIG_PATH)

CONFIG_FILE_PATH = get_default_config_path()

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
                bak_path = f"{self.config_path}.bak"
                logger.log(f"Erro ao ler '{self.config_path}': {e}. Criando backup em '{bak_path}' e restaurando padrão seguro.", "WARNING")
                try:
                    shutil.copy2(self.config_path, bak_path)
                except Exception as bak_err:
                    logger.log(f"Falha ao criar backup do config corrompido: {bak_err}", "WARNING")
                self.config = create_default_config()
                self._save_unlocked()

            return self.config

    def save(self):
        with self._lock:
            self._save_unlocked()

    def _save_unlocked(self):
        tmp_path = f"{self.config_path}.tmp"
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(self.config.to_dict(), f, indent=2, ensure_ascii=False)
            os.replace(tmp_path, self.config_path)

            # Sincroniza também o config.json local da raiz do projeto se existir e for caminho distinto
            try:
                resolved_active = Path(self.config_path).resolve()
                resolved_local = LOCAL_CONFIG_PATH.resolve()
                if LOCAL_CONFIG_PATH.exists() and resolved_active != resolved_local:
                    local_tmp = f"{LOCAL_CONFIG_PATH}.tmp"
                    with open(local_tmp, "w", encoding="utf-8") as f:
                        json.dump(self.config.to_dict(), f, indent=2, ensure_ascii=False)
                    os.replace(local_tmp, LOCAL_CONFIG_PATH)
            except Exception as loc_e:
                logger.log(f"Aviso ao sincronizar config local: {loc_e}", "DEBUG")

            event_bus.publish("on_config_updated", config=self.config)
        except Exception as e:
            logger.log(f"Erro ao salvar configurações em '{self.config_path}': {e}", "ERROR")
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass

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

    def import_profile(self, profile_data: Dict[str, Any]) -> bool:
        """Importa um perfil externo, desativando custom_command por segurança até revisão manual (H5)."""
        with self._lock:
            try:
                profile = ProfileConfig.from_dict(profile_data)
                if not profile.name or profile.name in self.config.profiles:
                    return False

                # Desativa custom_command em perfis importados até o usuário revisar (H5)
                for g_id, g_cfg in profile.gestures.items():
                    if g_cfg.action.action_type == "custom_command":
                        g_cfg.active = False
                        g_cfg.action.confirm_required = True
                        logger.log(
                            f"Gesto '{g_id}' com comando do sistema desativado por segurança no perfil '{profile.name}'.",
                            "WARNING"
                        )

                self.config.profiles[profile.name] = profile
                self._save_unlocked()
                logger.log(f"Perfil '{profile.name}' importado com sucesso.")
                return True
            except Exception as e:
                logger.log(f"Erro ao importar perfil: {e}", "ERROR")
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
