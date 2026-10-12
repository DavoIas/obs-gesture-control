import math
from typing import List, Tuple, Dict, Any, Optional

def dist_3d(p1, p2) -> float:
    return math.sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2 + (getattr(p1, 'z', 0.0) - getattr(p2, 'z', 0.0))**2)

class GestureRecognizer:
    """
    Reconhecedor estatístico e geométrico dos 8 gestos pré-definidos do sistema.
    Calcula extensões dos dedos, graus de confiança (0-100%) e previne conflitos de prioridade.
    """

    @staticmethod
    def is_extended(landmarks, tip_idx: int, pip_idx: int, wrist_idx: int = 0) -> bool:
        wrist = landmarks[wrist_idx]
        tip = landmarks[tip_idx]
        pip = landmarks[pip_idx]
        return dist_3d(tip, wrist) > (dist_3d(pip, wrist) * 1.05)

    def evaluate_hand(self, landmarks) -> Tuple[str, float]:
        """
        Avalia os landmarks de uma mão e retorna (gesto_id, confianca_0_a_1).
        """
        if not landmarks or len(landmarks) < 21:
            return "unknown", 0.0

        wrist = landmarks[0]
        thumb_tip, thumb_mcp = landmarks[4], landmarks[2]
        index_tip, index_pip, index_mcp = landmarks[8], landmarks[6], landmarks[5]
        middle_tip, middle_pip, middle_mcp = landmarks[12], landmarks[10], landmarks[9]
        ring_tip, ring_pip, ring_mcp = landmarks[16], landmarks[14], landmarks[13]
        pinky_tip, pinky_pip, pinky_mcp = landmarks[20], landmarks[18], landmarks[17]

        # Estado dos 4 dedos principais (Indicador, Médio, Anelar, Mínimo)
        idx_ext = self.is_extended(landmarks, 8, 6)
        mid_ext = self.is_extended(landmarks, 12, 10)
        rng_ext = self.is_extended(landmarks, 16, 14)
        pnk_ext = self.is_extended(landmarks, 20, 18)

        # Estado do Polegar
        thumb_dist_pinky = dist_3d(thumb_tip, pinky_mcp)
        thumb_ext = thumb_dist_pinky > (dist_3d(thumb_mcp, pinky_mcp) * 1.10)
        thumb_up = (thumb_tip.y < thumb_mcp.y - 0.03) and (thumb_tip.y < wrist.y)
        thumb_down = (thumb_tip.y > thumb_mcp.y + 0.03) and (thumb_tip.y > wrist.y)

        # Distância de pinça entre indicador e polegar
        pinch_dist = dist_3d(thumb_tip, index_tip)

        scores: Dict[str, float] = {}

        # 1. PEACE (✌️): Indicador e Médio estendidos; Anelar e Mínimo NÃO estendidos
        if idx_ext and mid_ext and not rng_ext and not pnk_ext:
            v_spread = dist_3d(index_tip, middle_tip)
            scores["peace"] = min(0.98, 0.88 + v_spread * 0.5)

        # 2. THUMBS_UP (👍): Polegar apontando para cima; 4 dedos dobrados
        if thumb_up and not idx_ext and not mid_ext and not rng_ext and not pnk_ext:
            scores["thumbs_up"] = 0.96

        # 3. THUMBS_DOWN (👎): Polegar apontando para baixo; 4 dedos dobrados
        if thumb_down and not idx_ext and not mid_ext and not rng_ext and not pnk_ext:
            scores["thumbs_down"] = 0.96

        # 4. OPEN_HAND (🖐️): Todos os 5 dedos estendidos
        if idx_ext and mid_ext and rng_ext and pnk_ext:
            scores["open_hand"] = 0.96

        # 5. FIST (✊): Nenhum dos 4 dedos estendido e polegar não apontado
        if not idx_ext and not mid_ext and not rng_ext and not pnk_ext and not thumb_up and not thumb_down:
            scores["fist"] = 0.94

        # 6. POINT (☝️): Apenas o Indicador estendido
        if idx_ext and not mid_ext and not rng_ext and not pnk_ext:
            scores["point"] = 0.95

        # 7. LOVE_YOU (🤟): Indicador, Mínimo e Polegar estendidos; Médio e Anelar dobrados
        if idx_ext and pnk_ext and thumb_ext and not mid_ext and not rng_ext:
            scores["love_you"] = 0.96

        # 8. PINCH (🤏): Ponta do Polegar e Indicador muito próximas
        if pinch_dist < 0.065:
            scores["pinch"] = min(0.98, 0.82 + (0.065 - pinch_dist) * 4.0)

        if not scores:
            return "unknown", 0.0

        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        best_gesture, best_confidence = sorted_scores[0]

        if len(sorted_scores) > 1:
            second_gesture, second_confidence = sorted_scores[1]
            if (best_confidence - second_confidence) < 0.08:
                return "undefined", 0.50

        return best_gesture, best_confidence
