import os
import json
import tempfile
import pytest
from app.config.models import (
    AppConfig, GestureConfig, ActionConfig, OBSConnectionConfig, CameraConfig, ProfileConfig
)
from app.config.manager import ConfigManager

def test_roundtrip_to_dict_from_dict():
    """Testa serialização e desserialização completa de todas as entidades de configuração."""
    act = ActionConfig(action_type="switch_scene", scene_name="Gameplay", confirm_required=True)
    g = GestureConfig(
        gesture_id="peace", icon="✌️", default_name="Peace", custom_name="Paz",
        description="Troca cena", active=True, action=act, cooldown=2.0, required_frames=10, sensitivity=80
    )
    d = g.to_dict()
    g_restored = GestureConfig.from_dict(d)
    assert g_restored.gesture_id == "peace"
    assert g_restored.cooldown == 2.0
    assert g_restored.action.scene_name == "Gameplay"
    assert g_restored.action.confirm_required is True

def test_clamps_validation():
    """Verifica limites e sanitização de dados (C6)."""
    # Cooldown negativo vira 0.0, required_frames fora do range 1..60, sensitivity fora de 0..100
    g = GestureConfig.from_dict({
        "gesture_id": "peace",
        "cooldown": -3.5,
        "required_frames": 999,
        "sensitivity": 120
    })
    assert g.cooldown == 0.0
    assert g.required_frames == 60
    assert g.sensitivity == 100

    g_low = GestureConfig.from_dict({
        "gesture_id": "peace",
        "required_frames": 0,
        "sensitivity": -10
    })
    assert g_low.required_frames == 1
    assert g_low.sensitivity == 0

    # OBS port (1..65535)
    obs_hi = OBSConnectionConfig.from_dict({"port": 70000})
    obs_lo = OBSConnectionConfig.from_dict({"port": 0})
    assert obs_hi.port == 65535
    assert obs_lo.port == 1

    # Camera target_fps (5..60)
    cam_hi = CameraConfig.from_dict({"target_fps": 120})
    cam_lo = CameraConfig.from_dict({"target_fps": 2})
    assert cam_hi.target_fps == 60
    assert cam_lo.target_fps == 5

    # Gestos desconhecidos são ignorados em ProfileConfig
    prof = ProfileConfig.from_dict({
        "name": "Custom",
        "gestures": {
            "peace": {"gesture_id": "peace"},
            "hacker_gesture": {"gesture_id": "hacker_gesture"}
        }
    })
    assert "peace" in prof.gestures
    assert "hacker_gesture" not in prof.gestures

def test_corrupted_config_creates_backup():
    """Verifica se JSON corrompido gera arquivo .bak e restaura padrão (C5)."""
    fd, tmp_path = tempfile.mkstemp(suffix=".json")
    os.close(fd)

    try:
        # Grava JSON inválido
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write("{invalid_json: 123,")

        cm = ConfigManager()
        cm.config_path = tmp_path
        loaded_cfg = cm.load()

        bak_path = f"{tmp_path}.bak"
        assert os.path.exists(bak_path)
        with open(bak_path, "r", encoding="utf-8") as bf:
            assert "{invalid_json" in bf.read()

        assert loaded_cfg is not None
        assert loaded_cfg.active_profile == "Live Gaming"
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        bak = f"{tmp_path}.bak"
        if os.path.exists(bak):
            os.remove(bak)


def test_gesture_edit_dialog_save_switching_actions():
    """Valida se o modal de edição de gestos salva corretamente mesmo ao alternar tipos de ações dinâmicas."""
    import customtkinter as ctk
    from app.gui.main_window import GestureEditDialog

    root = ctk.CTk()
    root.withdraw()

    saved = False

    def on_save():
        nonlocal saved
        saved = True

    try:
        dlg = GestureEditDialog(root, "three", on_save)
        # Troca para troca de cena
        dlg.combo_action.set("Trocar cena do OBS")
        dlg._on_action_type_changed("Trocar cena do OBS")

        # Troca para alternar mute
        dlg.combo_action.set("Alternar mute")
        dlg._on_action_type_changed("Alternar mute")

        # Executa save
        dlg._save()
        assert saved is True

        active_p = ConfigManager().get_active_profile()
        assert active_p.gestures["three"].action.action_type == "toggle_mute"
        assert active_p.gestures["three"].action.source_name == "Mic/Aux"
    finally:
        root.destroy()
