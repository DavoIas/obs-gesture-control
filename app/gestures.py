import math
from typing import Dict, Any, List

class GestureRecognizer:
    """
    Classe responsável por identificar gestos a partir dos landmarks da mão do MediaPipe.
    """
    def __init__(self):
        # Mapeamento extensível de detectores de gestos
        self._detectors = {
            "peace": self._detect_peace,
            "three": self._detect_three,
            "thumbs_up": self._detect_thumbs_up,
            "thumbs_down": self._detect_thumbs_down,
            "open_hand": self._detect_open_hand,
            "fist": self._detect_fist,
            "point": self._detect_point,
        }

    def detect_gesture(self, hand_landmarks) -> str:
        """
        Analisa a estrutura de landmarks da mão e retorna o nome do gesto detectado ou 'unknown'.
        
        :param hand_landmarks: Objeto de landmarks da mão vindo do MediaPipe Hands.
        :return: String com o gesto ('peace', 'thumbs_up', 'fist', etc.) ou 'unknown'.
        """
        if not hand_landmarks or not hasattr(hand_landmarks, 'landmark'):
            return "unknown"

        # Testa os detectores registrados
        for name, detector in self._detectors.items():
            try:
                if detector(hand_landmarks.landmark):
                    return name
            except Exception as e:
                # Evita falhas caso a leitura de landmarks venha malformada
                continue

        return "unknown"

    def _detect_peace(self, landmarks: List[Any]) -> bool:
        """
        Reconhece o gesto ✌️ Peace Sign:
        - Indicador e Médio levantados (extendidos);
        - Anelar e Mindinho abaixados (dobrados);
        - Polegar dobrado / próximo à palma;
        - Separação adequada entre pontas dos dedos indicador e médio.
        """
        # Índices dos Landmarks:
        # WRIST: 0
        # THUMB: 1..4 (TIP=4, IP=3, MCP=2)
        # INDEX: 5..8 (TIP=8, PIP=6, MCP=5)
        # MIDDLE: 9..12 (TIP=12, PIP=10, MCP=9)
        # RING: 13..16 (TIP=16, PIP=14, MCP=13)
        # PINKY: 17..20 (TIP=20, PIP=18, MCP=17)

        # 1. Indicador levantado: TIP (8) acima de PIP (6) e MCP (5)
        index_extended = (landmarks[8].y < landmarks[6].y) and (landmarks[6].y < landmarks[5].y)

        # 2. Médio levantado: TIP (12) acima de PIP (10) e MCP (9)
        middle_extended = (landmarks[12].y < landmarks[10].y) and (landmarks[10].y < landmarks[9].y)

        # 3. Anelar dobrado: TIP (16) abaixo de PIP (14)
        ring_folded = (landmarks[16].y > landmarks[14].y)

        # 4. Mindinho dobrado: TIP (20) abaixo de PIP (18)
        pinky_folded = (landmarks[20].y > landmarks[18].y)

        # 5. Distância entre pontas do indicador e médio para garantir formato de 'V'
        dist_index_middle = math.hypot(landmarks[8].x - landmarks[12].x, landmarks[8].y - landmarks[12].y)
        v_shape = dist_index_middle > 0.025

        # 6. Polegar não pode estar levantado junto com os outros (deve estar recolhido)
        thumb_not_up = (landmarks[4].y > landmarks[5].y) or (landmarks[4].y > landmarks[3].y) or (landmarks[4].y > landmarks[8].y)

        return index_extended and middle_extended and ring_folded and pinky_folded and v_shape and thumb_not_up

    def _detect_three(self, landmarks: List[Any]) -> bool:
        """
        Reconhece o gesto do número 3 (🤟 / 3 dedos levantados):
        Suporta duas variações clássicas de 3 dedos:
        - Variação A: Indicador, Médio e Anelar levantados; Mindinho dobrado.
        - Variação B: Polegar, Indicador e Médio levantados; Anelar e Mindinho dobrados.
        """
        index_extended = (landmarks[8].y < landmarks[6].y) and (landmarks[6].y < landmarks[5].y)
        middle_extended = (landmarks[12].y < landmarks[10].y) and (landmarks[10].y < landmarks[9].y)

        if not (index_extended and middle_extended):
            return False

        # Variação A: Indicador (8) + Médio (12) + Anelar (16) estendidos; Mindinho (20) dobrado
        ring_extended = (landmarks[16].y < landmarks[14].y)
        pinky_folded = (landmarks[20].y > landmarks[18].y)
        var_a = ring_extended and pinky_folded

        # Variação B: Polegar (4) + Indicador (8) + Médio (12) estendidos; Anelar (16) e Mindinho (20) dobrados
        ring_folded = (landmarks[16].y > landmarks[14].y)
        thumb_extended = (landmarks[4].y < landmarks[3].y) or (math.hypot(landmarks[4].x - landmarks[5].x, landmarks[4].y - landmarks[5].y) > 0.12)
        var_b = thumb_extended and ring_folded and pinky_folded

        return var_a or var_b

    # -------------------------------------------------------------------------
    # Estruturas preparadas para gestos futuros (V2+)
    # -------------------------------------------------------------------------

    def _detect_thumbs_up(self, landmarks: List[Any]) -> bool:
        """Estrutura preparada para futuro gesto de Thumbs Up 👍"""
        return False

    def _detect_thumbs_down(self, landmarks: List[Any]) -> bool:
        """Estrutura preparada para futuro gesto de Thumbs Down 👎"""
        return False

    def _detect_open_hand(self, landmarks: List[Any]) -> bool:
        """Estrutura preparada para futuro gesto de Mão Aberta ✋"""
        return False

    def _detect_fist(self, landmarks: List[Any]) -> bool:
        """Estrutura preparada para futuro gesto de Punho Fechado ✊"""
        return False

    def _detect_point(self, landmarks: List[Any]) -> bool:
        """Estrutura preparada para futuro gesto de Apontar 👆"""
        return False
