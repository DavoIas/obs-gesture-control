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
    def finger_extension(landmarks, tip_idx: int, pip_idx: int, wrist_idx: int = 0) -> float:
        wrist = landmarks[wrist_idx]
        tip = landmarks[tip_idx]
        pip = landmarks[pip_idx]
        d_tip = dist_3d(tip, wrist)
        d_pip = dist_3d(pip, wrist)
        ratio = d_tip / max(0.0001, d_pip)
        # Mapeamento contínuo: ratio 0.85 (dobrado) a 1.25 (totalmente estendido)
        score = (ratio - 0.85) / 0.40
        return max(0.0, min(1.0, score))

    @classmethod
    def is_extended(cls, landmarks, tip_idx: int, pip_idx: int, wrist_idx: int = 0) -> bool:
        return cls.finger_extension(landmarks, tip_idx, pip_idx, wrist_idx) >= 0.5

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

        # Extensão contínua dos dedos principais (0.0 a 1.0)
        ext_idx = self.finger_extension(landmarks, 8, 6)
        ext_mid = self.finger_extension(landmarks, 12, 10)
        ext_rng = self.finger_extension(landmarks, 16, 14)
        ext_pnk = self.finger_extension(landmarks, 20, 18)

        curl_idx = 1.0 - ext_idx
        curl_mid = 1.0 - ext_mid
        curl_rng = 1.0 - ext_rng
        curl_pnk = 1.0 - ext_pnk

        # Estado e extensão contínua do Polegar
        thumb_dist_pinky = dist_3d(thumb_tip, pinky_mcp)
        thumb_mcp_dist_pinky = dist_3d(thumb_mcp, pinky_mcp)
        thumb_ratio = thumb_dist_pinky / max(0.0001, thumb_mcp_dist_pinky)
        thumb_ext = max(0.0, min(1.0, (thumb_ratio - 0.90) / 0.35))
        thumb_curl = 1.0 - thumb_ext

        # Escala da mão invariante à distância da câmera (R3)
        palm_size = max(0.01, dist_3d(wrist, middle_mcp))

        # Vetor do polegar: thumb_mcp -> thumb_tip comparado ao eixo vertical com tolerância angular (R4)
        dx_thumb = thumb_tip.x - thumb_mcp.x
        dy_thumb = thumb_tip.y - thumb_mcp.y
        thumb_len = math.hypot(dx_thumb, dy_thumb)
        cos_35_deg = math.cos(math.radians(35))

        thumb_up = False
        thumb_down = False
        if thumb_len > 0.001 and thumb_ext > 0.45:
            # Em coordenadas de imagem/vídeo, o eixo Y aponta para baixo (-dy é para cima)
            cos_up = (-dy_thumb) / thumb_len
            cos_down = (dy_thumb) / thumb_len
            thumb_up = (cos_up >= cos_35_deg) and (thumb_tip.y < wrist.y)
            thumb_down = (cos_down >= cos_35_deg) and (thumb_tip.y > wrist.y)

        # Distância de pinça normalizada pela escala da mão (R3)
        pinch_dist = dist_3d(thumb_tip, index_tip)
        norm_pinch = pinch_dist / palm_size

        scores: Dict[str, float] = {}

        # 1. PEACE (✌️): Indicador e Médio estendidos; Anelar e Mínimo dobrados
        if ext_idx > 0.45 and ext_mid > 0.45 and ext_rng < 0.55 and ext_pnk < 0.55:
            base_score = (ext_idx + ext_mid + curl_rng + curl_pnk) / 4.0
            scores["peace"] = round(0.70 + 0.28 * base_score, 3)

        # 2. THUMBS_UP (👍): Polegar alinhado para cima e estendido; 4 dedos dobrados (R4)
        if thumb_up and ext_idx < 0.55 and ext_mid < 0.55 and ext_rng < 0.55 and ext_pnk < 0.55:
            base_score = (curl_idx + curl_mid + curl_rng + curl_pnk + thumb_ext) / 5.0
            scores["thumbs_up"] = round(0.70 + 0.28 * base_score, 3)

        # 3. THUMBS_DOWN (👎): Polegar alinhado para baixo e estendido; 4 dedos dobrados (R4)
        if thumb_down and ext_idx < 0.55 and ext_mid < 0.55 and ext_rng < 0.55 and ext_pnk < 0.55:
            base_score = (curl_idx + curl_mid + curl_rng + curl_pnk + thumb_ext) / 5.0
            scores["thumbs_down"] = round(0.70 + 0.28 * base_score, 3)

        # 4. OPEN_HAND (🖐️): Todos os 5 dedos estendidos
        if ext_idx > 0.45 and ext_mid > 0.45 and ext_rng > 0.45 and ext_pnk > 0.45:
            base_score = (ext_idx + ext_mid + ext_rng + ext_pnk + thumb_ext) / 5.0
            scores["open_hand"] = round(0.70 + 0.28 * base_score, 3)

        # 5. FIST (✊): 4 dedos dobrados, polegar não apontado
        if ext_idx < 0.50 and ext_mid < 0.50 and ext_rng < 0.50 and ext_pnk < 0.50 and not thumb_up and not thumb_down:
            base_score = (curl_idx + curl_mid + curl_rng + curl_pnk + thumb_curl) / 5.0
            scores["fist"] = round(0.70 + 0.28 * base_score, 3)

        # 6. POINT (☝️): Apenas o Indicador estendido (e não pinçando com o polegar)
        if ext_idx > 0.45 and ext_mid < 0.55 and ext_rng < 0.55 and ext_pnk < 0.55 and norm_pinch >= 0.28:
            base_score = (ext_idx + curl_mid + curl_rng + curl_pnk) / 4.0
            scores["point"] = round(0.70 + 0.28 * base_score, 3)

        # 7. LOVE_YOU (🤟): Indicador, Mínimo e Polegar estendidos; Médio e Anelar dobrados
        if ext_idx > 0.45 and ext_pnk > 0.45 and thumb_ext > 0.40 and ext_mid < 0.55 and ext_rng < 0.55:
            base_score = (ext_idx + ext_pnk + thumb_ext + curl_mid + curl_rng) / 5.0
            scores["love_you"] = round(0.70 + 0.28 * base_score, 3)

        # 8. PINCH (🤏): Ponta do Polegar e Indicador muito próximas, sem que a mão esteja totalmente em punho fechado
        is_all_curled = (ext_idx < 0.40 and ext_mid < 0.40 and ext_rng < 0.40 and ext_pnk < 0.40)
        if norm_pinch < 0.30 and not is_all_curled:
            closeness = max(0.0, min(1.0, (0.30 - norm_pinch) / 0.30))
            scores["pinch"] = round(0.75 + 0.23 * closeness, 3)

        if not scores:
            return "unknown", 0.0

        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        best_gesture, best_confidence = sorted_scores[0]

        if len(sorted_scores) > 1:
            second_gesture, second_confidence = sorted_scores[1]
            if (best_confidence - second_confidence) < 0.08:
                return "undefined", 0.50

        return best_gesture, best_confidence
