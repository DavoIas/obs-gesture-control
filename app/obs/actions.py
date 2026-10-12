import subprocess
import threading
from typing import Tuple, Optional
from app.config.models import ActionConfig
from app.obs.controller import obs_controller
from app.core.logger import logger
from app.core.events import event_bus

class ActionExecutor:
    """
    Executa de forma thread-safe as 16 ações suportadas pelo sistema OBS Gesture Control V2.
    """

    @staticmethod
    def execute(action: ActionConfig, gesture_name: str = "") -> Tuple[bool, str]:
        act_type = action.action_type
        client = obs_controller.get_client()

        # Ações que exigem conexão com OBS
        obs_required_actions = [
            "switch_scene", "enable_source", "disable_source", "toggle_source",
            "start_stream", "stop_stream", "start_record", "stop_record",
            "pause_record", "resume_record", "toggle_record_pause",
            "set_volume", "mute_source", "unmute_source", "toggle_mute"
        ]

        if act_type in obs_required_actions and (not client or not obs_controller.is_connected):
            msg = f"Ação '{act_type}' cancelada: OBS Studio não está conectado."
            logger.log(msg, "WARNING")
            event_bus.publish("on_action_failed", gesture=gesture_name, action=act_type, reason="OBS não conectado")
            return False, msg

        try:
            if act_type == "switch_scene":
                scene = action.scene_name
                if not scene:
                    return False, "Nome da cena não especificado."
                client.set_current_program_scene(scene)
                msg = f"Cena alterada para '{scene}'"

            elif act_type == "enable_source":
                scene = action.scene_name or ActionExecutor._get_current_scene(client)
                source = action.source_name
                item_id = ActionExecutor._get_scene_item_id(client, scene, source)
                if item_id is not None:
                    client.set_scene_item_enabled(scene, item_id, True)
                    msg = f"Fonte '{source}' ativada na cena '{scene}'"
                else:
                    return False, f"Fonte '{source}' não encontrada na cena '{scene}'"

            elif act_type == "disable_source":
                scene = action.scene_name or ActionExecutor._get_current_scene(client)
                source = action.source_name
                item_id = ActionExecutor._get_scene_item_id(client, scene, source)
                if item_id is not None:
                    client.set_scene_item_enabled(scene, item_id, False)
                    msg = f"Fonte '{source}' desativada na cena '{scene}'"
                else:
                    return False, f"Fonte '{source}' não encontrada na cena '{scene}'"

            elif act_type == "toggle_source":
                scene = action.scene_name or ActionExecutor._get_current_scene(client)
                source = action.source_name
                item_id = ActionExecutor._get_scene_item_id(client, scene, source)
                if item_id is not None:
                    enabled = client.get_scene_item_enabled(scene, item_id).scene_item_enabled
                    client.set_scene_item_enabled(scene, item_id, not enabled)
                    status_str = "desativada" if enabled else "ativada"
                    msg = f"Fonte '{source}' {status_str} na cena '{scene}'"
                else:
                    return False, f"Fonte '{source}' não encontrada"

            elif act_type == "start_stream":
                client.start_stream()
                msg = "Transmissão iniciada!"

            elif act_type == "stop_stream":
                client.stop_stream()
                msg = "Transmissão encerrada!"

            elif act_type == "start_record":
                client.start_record()
                msg = "Gravação iniciada!"

            elif act_type == "stop_record":
                client.stop_record()
                msg = "Gravação parada!"

            elif act_type == "pause_record":
                client.pause_record()
                msg = "Gravação pausada!"

            elif act_type == "resume_record":
                client.resume_record()
                msg = "Gravação retomada!"

            elif act_type == "toggle_record_pause":
                client.toggle_record_pause()
                msg = "Pausa da gravação alternada!"

            elif act_type == "set_volume":
                source = action.source_name
                vol_db = action.volume_db
                if vol_db is None or not (-100.0 <= vol_db <= 26.0):
                    msg = f"Volume inválido: {vol_db}dB. O valor deve estar entre -100 e 26 dB."
                    logger.log(msg, "WARNING")
                    event_bus.publish("on_action_failed", gesture=gesture_name, action=act_type, reason=msg)
                    return False, msg
                client.set_input_volume(source, vol_db=vol_db)
                msg = f"Volume da fonte '{source}' alterado para {vol_db}dB"

            elif act_type == "mute_source":
                source = action.source_name
                client.set_input_mute(source, True)
                msg = f"Fonte '{source}' mutada!"

            elif act_type == "unmute_source":
                source = action.source_name
                client.set_input_mute(source, False)
                msg = f"Fonte '{source}' desmutada!"

            elif act_type == "toggle_mute":
                source = action.source_name
                client.toggle_input_mute(source)
                msg = f"Mute da fonte '{source}' alternado!"

            elif act_type == "custom_command":
                cmd = action.command_str
                if not cmd:
                    return False, "Nenhum comando especificado."
                subprocess.Popen(cmd, shell=True)
                msg = f"Comando personalizado executado: '{cmd}'"

            else:
                return False, f"Tipo de ação desconhecido: '{act_type}'"

            logger.log(f"[Ação Executada] {msg}")
            event_bus.publish("on_action_triggered", gesture=gesture_name, action=act_type, detail=msg)
            return True, msg

        except Exception as e:
            err_msg = f"Erro ao executar ação '{act_type}': {e}"
            logger.log(err_msg, "ERROR")
            event_bus.publish("on_action_failed", gesture=gesture_name, action=act_type, reason=str(e))
            return False, err_msg

    @staticmethod
    def _get_current_scene(client) -> str:
        try:
            return client.get_current_program_scene().current_program_scene_name
        except Exception:
            return ""

    @staticmethod
    def _get_scene_item_id(client, scene_name: str, source_name: str) -> Optional[int]:
        try:
            items = client.get_scene_item_list(scene_name).scene_items
            for item in items:
                name = item.get('sourceName', '') if isinstance(item, dict) else getattr(item, 'source_name', '')
                if name.lower() == source_name.lower():
                    return item.get('sceneItemId') if isinstance(item, dict) else getattr(item, 'scene_item_id', None)
        except Exception:
            pass
        return None
