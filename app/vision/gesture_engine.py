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
                cls._instance.last_triggered: Dict[str, float] = {}
                cls._instance.recent_confidences = []
                cls._instance.max_history = 15
                cls._instance.armed: Dict[str, bool] = {}
                cls._instance.release_counts: Dict[str, int] = {}
                cls._instance.rearm_frames = 3
            return cls._instance

    def process(self, detected_gesture: str, confidence: float) -> Dict[str, Any]:
        with self._lock:
            now = time.time()
            profile = config_manager.get_active_profile()
            app_cfg = config_manager.config

            gesture_cfg = profile.gestures.get(detected_gesture)
            sensitivity_threshold = (gesture_cfg.sensitivity / 100.0) if gesture_cfg else 0.70

            # Mecanismo soltar para rearmar (B3):
            # Só rearma um gesto desarmado quando o gesto detectado deixar de ser ele por pelo menos N frames (ex.: 3)
            active_detection = detected_gesture if (detected_gesture not in ["unknown", "undefined"] and confidence >= sensitivity_threshold) else "unknown"
            for g, is_armed in list(self.armed.items()):
                if not is_armed:
                    if active_detection != g:
                        self.release_counts[g] = self.release_counts.get(g, 0) + 1
                        if self.release_counts[g] >= self.rearm_frames:
                            self.armed[g] = True
                            self.release_counts[g] = 0
                    else:
                        self.release_counts[g] = 0

            # Atualizar histórico de confianças para barra de estabilidade (0 - 100%)
            self.recent_confidences.append(confidence if detected_gesture != "unknown" else 0.0)
            if len(self.recent_confidences) > self.max_history:
                self.recent_confidences.pop(0)

            avg_confidence = (sum(self.recent_confidences) / len(self.recent_confidences)) if self.recent_confidences else 0.0
            stability_pct = min(100, int(avg_confidence * 100))

            is_active = gesture_cfg.active if gesture_cfg else False
            req_frames = gesture_cfg.required_frames if gesture_cfg else 8
            cooldown_sec = gesture_cfg.cooldown if gesture_cfg else 1.5

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
            is_armed = self.armed.get(detected_gesture, True)
            last_triggered_for_gesture = self.last_triggered.get(detected_gesture, 0.0)
            if self.consecutive_count >= req_frames and is_armed:
                if (now - last_triggered_for_gesture) >= cooldown_sec:
                    self.last_triggered[detected_gesture] = now
                    self.armed[detected_gesture] = False
                    self.release_counts[detected_gesture] = 0
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
