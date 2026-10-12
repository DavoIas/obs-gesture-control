import pytest
from unittest.mock import MagicMock, patch
from app.config.models import ActionConfig
from app.obs.actions import ActionExecutor
from app.obs.controller import obs_controller

def test_set_input_volume_correct_call():
    """Verifica que set_volume chama client.set_input_volume(source, vol_db=...) corretamente (B2)."""
    mock_client = MagicMock()
    with patch.object(obs_controller, "get_client", return_value=mock_client), \
         patch.object(obs_controller, "is_connected", True):
        
        action = ActionConfig(action_type="set_volume", source_name="Mic/Aux", volume_db=-12.5)
        ok, msg = ActionExecutor.execute(action, gesture_name="TestGesture")

        assert ok is True
        mock_client.set_input_volume.assert_called_once_with("Mic/Aux", vol_db=-12.5)

def test_connection_error_calls_mark_disconnected():
    """Verifica que exceção de conexão durante execução de ação chama mark_disconnected (T4)."""
    mock_client = MagicMock()
    mock_client.switch_scene = MagicMock()
    mock_client.set_current_program_scene.side_effect = ConnectionError("WebSocket connection reset by peer")

    with patch.object(obs_controller, "get_client", return_value=mock_client), \
         patch.object(obs_controller, "is_connected", True), \
         patch.object(obs_controller, "mark_disconnected") as mock_mark_disc:
        
        action = ActionConfig(action_type="switch_scene", scene_name="Gameplay")
        ok, msg = ActionExecutor.execute(action, gesture_name="TestGesture")

        assert ok is False
        mock_mark_disc.assert_called_once()
        assert "Queda durante ação" in mock_mark_disc.call_args[0][0]
