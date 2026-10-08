import cv2
import time
import threading
import math
import os
import urllib.request
from typing import Optional, Callable, List, Any
from app.gestures import GestureRecognizer

# Suporte avançado MediaPipe (compatível com todas as versões do Python 3.11 a 3.14)
MP_AVAILABLE = False
HandLandmarker = None
HandLandmarkerOptions = None
BaseOptions = None
drawing_utils = None
HandLandmarksConnections = None

try:
    import mediapipe as mp
    from mediapipe.tasks.python.vision import HandLandmarker, HandLandmarkerOptions, drawing_utils, HandLandmarksConnections
    from mediapipe.tasks.python.core.base_options import BaseOptions
    MP_AVAILABLE = True
except Exception as e:
    print(f"[Camera] Aviso no carregamento do MediaPipe Tasks: {e}")
    MP_AVAILABLE = False


class LandmarkAdapter:
    """Adapta os landmarks do MediaPipe para a interface esperada pelo GestureRecognizer."""
    def __init__(self, x, y, z=0.0):
        self.x = x
        self.y = y
        self.z = z

class HandLandmarksAdapter:
    def __init__(self, landmark_list):
        self.landmark = [LandmarkAdapter(lm.x, lm.y, getattr(lm, 'z', 0.0)) for lm in landmark_list]


class CameraHandler:
    """
    Gerenciador da captura da webcam e detecção de gestos via MediaPipe em thread separada.
    """
    MODEL_PATH = "hand_landmarker.task"
    MODEL_URL = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"

    def __init__(self, device_index: int = 0, required_consecutive_frames: int = 5):
        self.device_index = device_index
        self.required_consecutive_frames = required_consecutive_frames

        self.cap: Optional[cv2.VideoCapture] = None
        self.is_running = False
        self._thread: Optional[threading.Thread] = None

        self.recognizer = GestureRecognizer()

        # Rastreamento de gestos e cooldown
        self.consecutive_count = 0
        self.current_candidate_gesture = "unknown"
        self.last_triggered_time = 0.0
        self.cooldown_seconds = 1.5

        # Callbacks
        self.on_frame: Optional[Callable] = None
        self.on_gesture_triggered: Optional[Callable[[str], None]] = None
        self.on_status_change: Optional[Callable[[bool, str], None]] = None

        # MediaPipe Landmarker
        self.landmarker = None
        self._init_mediapipe()

    def _init_mediapipe(self):
        """Inicializa o modelo HandLandmarker do MediaPipe."""
        if not MP_AVAILABLE:
            print("[Camera] MediaPipe não disponível no ambiente.")
            return

        # Garante que o modelo task esteja baixado
        if not os.path.exists(self.MODEL_PATH):
            try:
                print(f"[Camera] Baixando modelo do MediaPipe ({self.MODEL_PATH})...")
                urllib.request.urlretrieve(self.MODEL_URL, self.MODEL_PATH)
                print("[Camera] Modelo baixado com sucesso!")
            except Exception as e:
                print(f"[Camera] Erro ao baixar modelo MediaPipe: {e}")
                return

        try:
            options = HandLandmarkerOptions(
                base_options=BaseOptions(model_asset_path=self.MODEL_PATH),
                num_hands=1
            )
            self.landmarker = HandLandmarker.create_from_options(options)
            print("[Camera] Detector de mãos MediaPipe (HandLandmarker) inicializado!")
        except Exception as e:
            print(f"[Camera] Falha ao instanciar HandLandmarker: {e}")
            self.landmarker = None

    def set_cooldown(self, cooldown: float):
        """Atualiza o tempo de cooldown entre disparos de ação."""
        self.cooldown_seconds = max(0.1, cooldown)

    def set_device_index(self, device_index: int):
        """Atualiza o índice da câmera e reinicia a captura se estiver rodando."""
        was_running = self.is_running
        if was_running:
            self.stop()
        self.device_index = device_index
        if was_running:
            self.start()

    def _try_open_capture(self, index: int, check_brightness: bool = False) -> Optional[cv2.VideoCapture]:
        """Tenta abrir uma câmera pelo índice usando DSHOW ou MSMF."""
        backends = [cv2.CAP_DSHOW, cv2.CAP_MSMF] if cv2.os.name == 'nt' else [cv2.CAP_ANY]
        for backend in backends:
            try:
                cap = cv2.VideoCapture(index, backend)
                if cap and cap.isOpened():
                    ret, frame = cap.read()
                    if ret and frame is not None:
                        if check_brightness and frame.mean() < 2.0:
                            cap.release()
                            continue
                        return cap
                    cap.release()
            except Exception:
                pass
        return None

    def start(self) -> bool:
        """Inicia a captura da webcam em thread em segundo plano com busca automática de índice ativo."""
        if self.is_running:
            return True

        # Tenta o índice configurado primeiro
        self.cap = self._try_open_capture(self.device_index, check_brightness=False)
        
        # Se a câmera no índice atual não abrir ou for tela preta (Iriun inativo), busca automaticamente
        if self.cap:
            ret, frame = self.cap.read()
            if ret and frame is not None and frame.mean() < 2.0:
                print(f"[Camera] Câmera no índice {self.device_index} é uma tela preta (Iriun desconectado). Procurando câmera física...")
                self.cap.release()
                self.cap = None

        if not self.cap:
            print(f"[Camera] Buscando câmera ativa nos índices [2, 1, 0, 3]...")
            for alt_idx in [2, 1, 0, 3]:
                cap_alt = self._try_open_capture(alt_idx, check_brightness=True)
                if cap_alt:
                    self.device_index = alt_idx
                    self.cap = cap_alt
                    print(f"[Camera] Câmera ativa encontrada no índice {alt_idx}!")
                    break

        if not self.cap:
            msg = "Não foi possível obter vídeo de nenhuma webcam (testados índices 0, 1, 2)."
            print(f"[Camera] {msg}")
            self._notify_status(False, msg)
            return False

        self.is_running = True
        self._thread = threading.Thread(target=self._process_loop, daemon=True)
        self._thread.start()

        msg = f"Webcam (Dispositivo {self.device_index}) iniciada com sucesso."
        print(f"[Camera] {msg}")
        self._notify_status(True, msg)
        return True

    def stop(self):
        """Encerra a captura da webcam e libera recursos de forma segura."""
        self.is_running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        self._thread = None

        if self.cap:
            try:
                self.cap.release()
            except Exception:
                pass
            self.cap = None

        msg = "Câmera parada."
        print(f"[Camera] {msg}")
        self._notify_status(False, msg)

    def _notify_status(self, is_active: bool, msg: str):
        if hasattr(self, 'on_status_change') and self.on_status_change:
            try:
                self.on_status_change(is_active, msg)
            except Exception:
                pass

    def _process_loop(self):
        """Loop contínuo de leitura de frames e detecção de gestos com MediaPipe."""
        while self.is_running and self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if not ret or frame is None:
                time.sleep(0.03)
                continue

            # Inverte horizontalmente para modo espelho
            frame = cv2.flip(frame, 1)

            detected_gesture = "unknown"
            landmarks_obj = None

            # Processamento MediaPipe HandLandmarker
            if self.landmarker:
                try:
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
                    result = self.landmarker.detect(mp_image)

                    if result and result.hand_landmarks:
                        for hand_landmarks in result.hand_landmarks:
                            landmarks_obj = HandLandmarksAdapter(hand_landmarks)
                            # Desenha o esqueleto da mão na imagem do vídeo
                            if drawing_utils and HandLandmarksConnections:
                                drawing_utils.draw_landmarks(
                                    frame,
                                    hand_landmarks,
                                    HandLandmarksConnections.HAND_CONNECTIONS
                                )
                except Exception as e:
                    pass

            if landmarks_obj:
                detected_gesture = self.recognizer.detect_gesture(landmarks_obj)

            # Lógica de consistência de frames & Cooldown
            now = time.time()
            if detected_gesture in ["peace", "three"]:
                if self.current_candidate_gesture == detected_gesture:
                    self.consecutive_count += 1
                else:
                    self.current_candidate_gesture = detected_gesture
                    self.consecutive_count = 1

                # Desenha aviso visual direto na imagem do vídeo
                gesture_text = "PEACE ✌️" if detected_gesture == "peace" else "NÚMERO 3 🤟"
                cv2.putText(
                    frame, f"GESTO DETECTADO: {gesture_text}", (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (166, 227, 161), 2, cv2.LINE_AA
                )

                # Se detectado consistentemente por N frames consecutivos
                if self.consecutive_count >= self.required_consecutive_frames:
                    if now - self.last_triggered_time >= self.cooldown_seconds:
                        self.last_triggered_time = now
                        triggered = self.current_candidate_gesture
                        self.consecutive_count = 0  # Reseta contador pós disparo
                        print(f"[Camera] GESTO '{triggered}' VALIDADO E DISPARADO!")
                        if self.on_gesture_triggered:
                            self.on_gesture_triggered(triggered)
            else:
                self.current_candidate_gesture = "unknown"
                self.consecutive_count = 0

            # Notifica frame pronto para atualização na GUI
            if self.on_frame:
                self.on_frame(frame, detected_gesture, self.current_candidate_gesture, self.consecutive_count)

            time.sleep(0.015)

    def __del__(self):
        try:
            self.stop()
        except Exception:
            pass
