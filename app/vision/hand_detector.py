import os
import urllib.request
import cv2
import numpy as np
from typing import Optional, List, Any, Tuple

MP_AVAILABLE = False
HandLandmarker = None
HandLandmarkerOptions = None
BaseOptions = None

try:
    import mediapipe as mp
    from mediapipe.tasks.python.vision import HandLandmarker, HandLandmarkerOptions
    from mediapipe.tasks.python.core.base_options import BaseOptions
    MP_AVAILABLE = True
except Exception as e:
    MP_AVAILABLE = False


class LandmarkAdapter:
    def __init__(self, x, y, z=0.0):
        self.x = x
        self.y = y
        self.z = z

class HandLandmarksAdapter:
    def __init__(self, landmark_list):
        self.landmark = [LandmarkAdapter(lm.x, lm.y, getattr(lm, 'z', 0.0)) for lm in landmark_list]


# Conexões dos 21 landmarks da mão para desenho OpenCV nativo
HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),        # Polegar
    (0, 5), (5, 6), (6, 7), (7, 8),        # Indicador
    (9, 10), (10, 11), (11, 12),           # Médio
    (13, 14), (14, 15), (15, 16),          # Anelar
    (0, 17), (17, 18), (18, 19), (19, 20),  # Mínimo
    (5, 9), (9, 13), (13, 17)              # Palma / Articulações
]

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

class HandDetector:
    """
    Invoca o MediaPipe HandLandmarker Tasks API localmente para até 2 mãos.
    Fornece renderização nativa em OpenCV do esqueleto 3D e pontos.
    """
    MODEL_PATH = str(ROOT / "hand_landmarker.task")
    MODEL_URL = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"

    def __init__(
        self,
        max_hands: int = 2,
        min_detection_confidence: float = 0.5,
        min_presence_confidence: float = 0.5,
        min_tracking_confidence: float = 0.5
    ):
        self.max_hands = max_hands
        self.min_detection_confidence = min_detection_confidence
        self.min_presence_confidence = min_presence_confidence
        self.min_tracking_confidence = min_tracking_confidence
        self.landmarker = None
        self._init_detector()

    def _init_detector(self):
        if not MP_AVAILABLE:
            print("[HandDetector] MediaPipe não disponível no ambiente.")
            return

        if not os.path.exists(self.MODEL_PATH):
            try:
                print(f"[HandDetector] Baixando modelo MediaPipe ({self.MODEL_PATH})...")
                urllib.request.urlretrieve(self.MODEL_URL, self.MODEL_PATH)
                print("[HandDetector] Modelo baixado com sucesso!")
            except Exception as e:
                print(f"[HandDetector] Erro ao baixar modelo MediaPipe: {e}")
                return

        try:
            options = HandLandmarkerOptions(
                base_options=BaseOptions(model_asset_path=self.MODEL_PATH),
                num_hands=self.max_hands,
                min_hand_detection_confidence=self.min_detection_confidence,
                min_hand_presence_confidence=self.min_presence_confidence,
                min_tracking_confidence=self.min_tracking_confidence
            )
            self.landmarker = HandLandmarker.create_from_options(options)
            print(f"[HandDetector] Detector de até {self.max_hands} mãos inicializado com sucesso!")
        except Exception as e:
            print(f"[HandDetector] Falha ao instanciar HandLandmarker: {e}")
            self.landmarker = None

    def draw_landmarks(self, frame_bgr: np.ndarray, raw_hand_landmarks_list: List[Any]):
        """Desenha o esqueleto neon e articulações da mão diretamente via OpenCV."""
        if frame_bgr is None or not raw_hand_landmarks_list:
            return

        h, w, _ = frame_bgr.shape

        for hand_landmarks in raw_hand_landmarks_list:
            lm_list = getattr(hand_landmarks, 'landmark', hand_landmarks)
            pts = []
            for lm in lm_list:
                px = int(lm.x * w)
                py = int(lm.y * h)
                pts.append((px, py))

            # Desenhar conexões da mão
            for p1_idx, p2_idx in HAND_CONNECTIONS:
                if p1_idx < len(pts) and p2_idx < len(pts):
                    cv2.line(frame_bgr, pts[p1_idx], pts[p2_idx], (0, 255, 120), 2, cv2.LINE_AA)

            # Desenhar nós/articulações
            for i, pt in enumerate(pts):
                color = (0, 0, 255) if i in [4, 8, 12, 16, 20] else (255, 200, 0)
                radius = 5 if i in [4, 8, 12, 16, 20] else 3
                cv2.circle(frame_bgr, pt, radius, color, -1, cv2.LINE_AA)
