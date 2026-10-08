import time
import threading
from typing import Dict, Any, Optional
from app.config.manager import config_manager
from app.obs.actions import ActionExecutor
from app.core.logger import logger
from app.core.events import event_bus

class GestureEngine:
    """
    Motor inteligente de verificação de gestos, estabilidade, cooldown e execução de ações.
    Aplica janela de confirmação de N frames, filtro anti-oscilação, modo teste e portão de segurança.
    """
    _instance = None
    _lock = threading.RLock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(GestureEngine, cls).__new__(cls)
                cls._instance.current_candidate = "unknown"
                cls._instance.consecutive_count = 0
                cls._instance.last_triggered_time = 0.0
                cls._instance.recent_confidences = []
                cls._instance.max_history = 15
            return cls._instance

    def process(self, detected_gesture: str, confidence: float) -> Dict[str, Any]:
        with self._lock:
            now = time.time()
            profile = config_manager.get_active_profile()
            app_cfg = config_manager.config

            # Atualizar histórico de confianças para barra de estabilidade (0 - 100%)
            self.recent_confidences.append(confidence if detected_gesture != "unknown" else 0.0)
            if len(self.recent_confidences) > self.max_history:
                self.recent_confidences.pop(0)

            avg_confidence = (sum(self.recent_confidences) / len(self.recent_confidences)) if self.recent_confidences else 0.0
            stability_pct = min(100, int(avg_confidence * 100))

            gesture_cfg = profile.gestures.get(detected_gesture)
            is_active = gesture_cfg.active if gesture_cfg else False
            req_frames = gesture_cfg.required_frames if gesture_cfg else 8
            cooldown_sec = gesture_cfg.cooldown if gesture_cfg else 1.5
            sensitivity_threshold = (gesture_cfg.sensitivity / 100.0) if gesture_cfg else 0.70

            # Caso gesto não esteja configurado, seja desconhecido ou inativo
            if detected_gesture in ["unknown", "undefined"] or not is_active or confidence < sensitivity_threshold:
                self.current_candidate = "unknown"
                self.consecutive_count = 0
                return {
                    "gesture": detected_gesture,
                    "confidence": int(confidence * 100),
                    "stability": stability_pct,
                    "consecutive": 0,
                    "required_frames": req_frames,
                    "triggered": False
                }

            # Lógica de contagem consecutiva
            if self.current_candidate == detected_gesture:
                self.consecutive_count += 1
            else:
                self.current_candidate = detected_gesture
                self.consecutive_count = 1

            triggered = False
            action_desc = ""

            # Se atingiu o número de frames exigido e o cooldown já passou
            if self.consecutive_count >= req_frames:
                if (now - self.last_triggered_time) >= cooldown_sec:
                    self.last_triggered_time = now
                    self.consecutive_count = 0  # Reseta contador após disparo
                    triggered = True

                    action_cfg = gesture_cfg.action
                    g_name = gesture_cfg.custom_name or gesture_cfg.default_name

                    # Verificar Modo Teste
                    if app_cfg.test_mode:
                        action_desc = f"[MODO TESTE] Ação simulada: '{action_cfg.action_type}' em '{g_name}'"
                        logger.log(action_desc, "INFO")
                        event_bus.publish("on_test_action_simulated", gesture=g_name, action=action_cfg.action_type)
                    else:
                        # Verificar se requer confirmação para ação destrutiva
                        if app_cfg.confirm_destructive_actions and action_cfg.confirm_required:
                            event_bus.publish("on_action_confirm_required", gesture=g_name, action=action_cfg)
                            action_desc = f"Solicitada confirmação para '{action_cfg.action_type}'"
                        else:
                            success, action_desc = ActionExecutor.execute(action_cfg, gesture_name=g_name)

            event_bus.publish(
                "on_gesture_processed",
                gesture=detected_gesture,
                confidence=int(confidence * 100),
                stability=stability_pct,
                consecutive=self.consecutive_count,
                required_frames=req_frames,
                triggered=triggered,
                action_desc=action_desc
            )

            return {
                "gesture": detected_gesture,
                "confidence": int(confidence * 100),
                "stability": stability_pct,
                "consecutive": self.consecutive_count,
                "required_frames": req_frames,
                "triggered": triggered,
                "action_desc": action_desc
            }

gesture_engine = GestureEngine()
