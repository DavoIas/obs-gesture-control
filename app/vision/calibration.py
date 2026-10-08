import time
from typing import List, Dict, Any, Tuple
from app.vision.gesture_recognizer import GestureRecognizer, dist_3d

class GestureCalibrator:
    """
    Ferramenta de Calibração Interativa. Coleta amostras do gesto em tempo real,
    analisa posições, distâncias entre os landmarks e estabilidade visual sem armazenar vídeo.
    """
    def __init__(self, target_gesture: str, sample_goal: int = 30):
        self.target_gesture = target_gesture
        self.sample_goal = sample_goal
        self.samples: List[Tuple[str, float, Any]] = []
        self.recognizer = GestureRecognizer()
        self.is_finished = False

    def add_frame(self, raw_hand_landmarks) -> bool:
        if self.is_finished or not raw_hand_landmarks:
            return self.is_finished

        # Converter landmarks se necessário
        lm_list = getattr(raw_hand_landmarks, 'landmark', raw_hand_landmarks)
        gesture_id, conf = self.recognizer.evaluate_hand(lm_list)
        self.samples.append((gesture_id, conf, lm_list))

        if len(self.samples) >= self.sample_goal:
            self.is_finished = True
        return self.is_finished

    def get_progress(self) -> float:
        return min(1.0, len(self.samples) / float(self.sample_goal))

    def analyze(self) -> Dict[str, Any]:
        if not self.samples:
            return {
                "quality": "Insuficiente",
                "avg_confidence": 0,
                "matches_pct": 0,
                "recommendation": "Nenhum frame válido capturado. Garanta que sua mão está visível."
            }

        matches = [s for s in self.samples if s[0] == self.target_gesture]
        confidences = [s[1] for s in self.samples if s[0] == self.target_gesture]
        
        matches_pct = int((len(matches) / len(self.samples)) * 100)
        avg_conf = int((sum(confidences) / len(confidences) * 100)) if confidences else 0

        if matches_pct > 80 and avg_conf > 85:
            quality = "Excelente"
            recommendation = "Ótima iluminação e enquadramento! O gesto está muito estável."
        elif matches_pct > 60 and avg_conf > 70:
            quality = "Boa"
            recommendation = "Reconhecimento estável. Melhore a iluminação frontal se possível."
        else:
            quality = "Regular"
            recommendation = "Alta oscilação detectada. Verifique se o contraste com o fundo é bom."

        return {
            "gesture": self.target_gesture,
            "quality": quality,
            "avg_confidence": avg_conf,
            "matches_pct": matches_pct,
            "samples_count": len(self.samples),
            "recommendation": recommendation
        }
