import pytest
from unittest.mock import patch, MagicMock
from app.vision.gesture_engine import GestureEngine
from app.config.manager import config_manager

@pytest.fixture
def engine():
    eng = GestureEngine()
    eng.consecutive_count = 0
    eng.current_candidate = "unknown"
    eng.last_triggered.clear()
    eng.armed.clear()
    eng.release_counts.clear()
    return eng

def test_n_frames_confirmation(engine):
    """Verifica que o gesto só dispara após atingir required_frames consecutivos."""
    profile = config_manager.get_active_profile()
    gesture_cfg = profile.gestures["peace"]
    req = gesture_cfg.required_frames
    gesture_cfg.cooldown = 0.0

    with patch("app.obs.actions.ActionExecutor.submit") as mock_submit:
        # Enviar req - 1 frames
        for _ in range(req - 1):
            res = engine.process("peace", 0.90)
            assert res["triggered"] is False

        mock_submit.assert_not_called()

        # Enviar o frame que atinge a meta
        res = engine.process("peace", 0.90)
        assert res["triggered"] is True
        mock_submit.assert_called_once()

def test_cooldown_per_gesture(engine):
    """Verifica que o cooldown de um gesto não bloqueia o disparo de outro gesto diferente (B4)."""
    profile = config_manager.get_active_profile()
    profile.gestures["peace"].cooldown = 5.0
    profile.gestures["peace"].required_frames = 2

    profile.gestures["point"].cooldown = 5.0
    profile.gestures["point"].required_frames = 2

    with patch("app.obs.actions.ActionExecutor.submit") as mock_submit:
        # Dispara peace
        engine.process("peace", 0.9)
        res_p = engine.process("peace", 0.9)
        assert res_p["triggered"] is True
        assert mock_submit.call_count == 1

        # Tenta disparar peace de novo imediatamente -> em cooldown
        engine.process("unknown", 0.0)
        engine.process("peace", 0.9)
        res_p2 = engine.process("peace", 0.9)
        assert res_p2["triggered"] is False

        # Mas point deve conseguir disparar se cumprir seus frames (cooldown independente)
        engine.process("unknown", 0.0)
        engine.process("point", 0.9)
        res_pt = engine.process("point", 0.9)
        assert res_pt["triggered"] is True
        assert mock_submit.call_count == 2

def test_release_to_rearm(engine):
    """Verifica que após disparar, o gesto só dispara de novo se for solto por N frames (B3)."""
    profile = config_manager.get_active_profile()
    profile.gestures["peace"].cooldown = 0.0  # sem cooldown de tempo
    profile.gestures["peace"].required_frames = 1

    with patch("app.obs.actions.ActionExecutor.submit") as mock_submit:
        # Disparo 1
        res1 = engine.process("peace", 0.9)
        assert res1["triggered"] is True
        assert mock_submit.call_count == 1

        # Mesmo sem cooldown, continuar segurando a mão não deve redisparar continuamente
        res2 = engine.process("peace", 0.9)
        assert res2["triggered"] is False
        assert mock_submit.call_count == 1

        # Soltar a mão por menos que rearm_frames (ex: 2 frames)
        engine.process("unknown", 0.0)
        engine.process("unknown", 0.0)
        # Ainda não rearmou
        res3 = engine.process("peace", 0.9)
        assert res3["triggered"] is False

        # Soltar pelo 3º frame consecutivo -> rearma!
        engine.process("unknown", 0.0)
        engine.process("unknown", 0.0)
        engine.process("unknown", 0.0)

        # Agora ao fazer peace, deve disparar de novo
        res4 = engine.process("peace", 0.9)
        assert res4["triggered"] is True
        assert mock_submit.call_count == 2

def test_test_mode_does_not_execute(engine):
    """Verifica que com test_mode=True nenhuma ação externa é enviada ao OBS."""
    config_manager.set_test_mode(True)
    profile = config_manager.get_active_profile()
    profile.gestures["peace"].required_frames = 1
    profile.gestures["peace"].cooldown = 0.0

    try:
        with patch("app.obs.actions.ActionExecutor.submit") as mock_submit:
            res = engine.process("peace", 0.9)
            assert res["triggered"] is True
            assert "[MODO TESTE]" in res["action_desc"]
            mock_submit.assert_not_called()
    finally:
        config_manager.set_test_mode(False)
