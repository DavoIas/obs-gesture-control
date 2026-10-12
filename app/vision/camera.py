import os
import cv2
import time
import threading
import numpy as np
import mediapipe as mp
from typing import Optional, Callable, List, Tuple, Any, Dict
from app.config.manager import config_manager
from app.vision.hand_detector import HandDetector, HandLandmarksAdapter
from app.vision.gesture_recognizer import GestureRecognizer
from app.vision.gesture_engine import gesture_engine
from app.core.logger import logger
from app.core.events import event_bus

class CameraHandler:
    """
    Gerenciador thread-safe da captura da webcam em segundo plano.
    Executa a visão computacional, o desenho de landmarks, overlay visual e o processamento de gestos.
    """
    _instance = None
    _lock = threading.RLock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(CameraHandler, cls).__new__(cls)
                cls._instance.cap: Optional[cv2.VideoCapture] = None
                cls._instance.is_running = False
                cls._instance._thread: Optional[threading.Thread] = None
                cam_cfg = config_manager.config.camera
                cls._instance.detector = HandDetector(
                    max_hands=cam_cfg.max_hands,
                    min_detection_confidence=cam_cfg.min_detection_confidence,
                    min_presence_confidence=cam_cfg.min_presence_confidence,
                    min_tracking_confidence=cam_cfg.min_tracking_confidence
                )
                cls._instance.recognizer = GestureRecognizer()
                cls._instance.on_frame_callbacks: List[Callable] = []
            return cls._instance

    def add_on_frame_listener(self, callback: Callable):
        with self._lock:
            if callback not in self.on_frame_callbacks:
                self.on_frame_callbacks.append(callback)

    def remove_on_frame_listener(self, callback: Callable):
        with self._lock:
            if callback in self.on_frame_callbacks:
                self.on_frame_callbacks.remove(callback)

    def _try_open(self, idx: int) -> Optional[cv2.VideoCapture]:
        backends = [cv2.CAP_DSHOW, cv2.CAP_MSMF] if os.name == 'nt' else [cv2.CAP_ANY]
        for backend in backends:
            try:
                cap = cv2.VideoCapture(idx, backend)
                if cap and cap.isOpened():
                    ret, frame = cap.read()
                    if ret and frame is not None and frame.mean() >= 10.0:
                        return cap
                    cap.release()
            except Exception:
                pass
        return None

    def start(self) -> bool:
        with self._lock:
            if self.is_running:
                return True

            cam_cfg = config_manager.config.camera
            target_idx = cam_cfg.device_index

            logger.log(f"Iniciando captura de vídeo na câmera (Dispositivo {target_idx})...")
            self.cap = self._try_open(target_idx)

            self.current_device_index = target_idx
            if not self.cap:
                logger.log(f"Câmera no índice {target_idx} indisponível ou tela preta. Procurando webcam física ativa...", "WARNING")
                for alt_idx in range(0, 5):
                    if alt_idx == target_idx:
                        continue
                    cap_alt = self._try_open(alt_idx)
                    if cap_alt:
                        self.cap = cap_alt
                        self.current_device_index = alt_idx
                        logger.log(f"Câmera ativa com imagem real encontrada no índice {alt_idx}!")
                        event_bus.publish("on_camera_fallback", fallback_index=alt_idx, original_index=target_idx)
                        break

            if not self.cap:
                msg = "Não foi possível abrir nenhuma câmera (testados índices 0 a 4)."
                logger.log(msg, "ERROR")
                event_bus.publish("on_camera_status", active=False, message=msg)
                return False

            # Aplicar resolução configurada (C1)
            if cam_cfg.resolution_width and cam_cfg.resolution_height:
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, cam_cfg.resolution_width)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, cam_cfg.resolution_height)

            # Sincronizar detector com max_hands e confianças do config (C1 / R6)
            if (self.detector.max_hands != cam_cfg.max_hands or
                self.detector.min_detection_confidence != cam_cfg.min_detection_confidence or
                self.detector.min_presence_confidence != cam_cfg.min_presence_confidence or
                self.detector.min_tracking_confidence != cam_cfg.min_tracking_confidence):
                self.detector = HandDetector(
                    max_hands=cam_cfg.max_hands,
                    min_detection_confidence=cam_cfg.min_detection_confidence,
                    min_presence_confidence=cam_cfg.min_presence_confidence,
                    min_tracking_confidence=cam_cfg.min_tracking_confidence
                )

            self.is_running = True
            self._thread = threading.Thread(target=self._process_loop, daemon=True)
            self._thread.start()

            msg = f"Câmera iniciada com sucesso (Dispositivo {self.current_device_index})"
            logger.log(msg)
            event_bus.publish("on_camera_status", active=True, message=msg)
            return True

    def stop(self):
        thread = None
        with self._lock:
            if not self.is_running and not self._thread and not self.cap:
                return
            self.is_running = False
            thread = self._thread
            self._thread = None

        # Aguardar encerramento da thread fora do lock para evitar deadlock
        if thread and thread.is_alive():
            thread.join(timeout=2.0)

        with self._lock:
            if self.cap:
                try:
                    self.cap.release()
                except Exception:
                    pass
                self.cap = None
            msg = "Câmera parada."
            logger.log(msg)
            event_bus.publish("on_camera_status", active=False, message=msg)

    def _process_loop(self):
        last_frame_time = time.perf_counter()
        fps_history = []
        current_fps = 0.0

        while self.is_running and self.cap and self.cap.isOpened():
            start_loop = time.perf_counter()
            ret, frame = self.cap.read()
            if not ret or frame is None:
                time.sleep(0.01)
                continue

            # Espelhamento horizontal para experiência natural do usuário
            frame = cv2.flip(frame, 1)

            cam_cfg = config_manager.config.camera

            # Processar mãos com MediaPipe
            raw_hands = []
            handedness_list = []
            if self.detector.landmarker:
                try:
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    frame_rgb = np.ascontiguousarray(frame_rgb)
                    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
                    result = self.detector.landmarker.detect(mp_image)
                    if result and result.hand_landmarks:
                        raw_hands = result.hand_landmarks
                        handedness_list = getattr(result, 'handedness', []) or []
                except Exception as e:
                    print(f"[Camera] MediaPipe detect error: {e}")

            detected_gesture = "unknown"
            confidence = 0.0

            # Reconhecimento considerando a mão preferida configurada (R6)
            if raw_hands:
                pref_hand = cam_cfg.preferred_hand.lower()
                chosen_idx = 0
                if pref_hand in ["left", "right"] and len(raw_hands) > 1:
                    for idx in range(len(raw_hands)):
                        if idx < len(handedness_list) and handedness_list[idx]:
                            cat = handedness_list[idx][0]
                            lbl = getattr(cat, 'category_name', getattr(cat, 'display_name', '')).lower()
                            # Devido ao cv2.flip anterior, a lateralidade física do usuário é invertida
                            real_hand = "right" if lbl == "left" else ("left" if lbl == "right" else "")
                            if real_hand == pref_hand:
                                chosen_idx = idx
                                break

                hand_adapter = HandLandmarksAdapter(raw_hands[chosen_idx])
                detected_gesture, confidence = self.recognizer.evaluate_hand(hand_adapter.landmark)

                # Desenhar esqueleto se ativado nas configurações
                if cam_cfg.draw_landmarks:
                    self.detector.draw_landmarks(frame, raw_hands)

            # Processar lógica no GestureEngine
            engine_result = gesture_engine.process(detected_gesture, confidence)
            engine_result["real_fps"] = current_fps

            # Desenhar Overlay na Imagem (se ativado)
            if cam_cfg.draw_overlay:
                self._draw_overlay(frame, engine_result, current_fps)

            # Notificar listeners de GUI com a cópia do frame
            with self._lock:
                listeners = list(self.on_frame_callbacks)
            
            for cb in listeners:
                try:
                    cb(frame, engine_result, raw_hands)
                except Exception as e:
                    pass

            # Controlar taxa de FPS dormindo apenas o restante do frame interval (T5)
            elapsed = time.perf_counter() - start_loop
            target_fps = max(10, cam_cfg.target_fps)
            frame_interval = 1.0 / target_fps
            sleep_time = max(0.0, frame_interval - elapsed)
            if sleep_time > 0:
                time.sleep(sleep_time)

            # Cálculo do FPS real
            now = time.perf_counter()
            dt = now - last_frame_time
            last_frame_time = now
            if dt > 0:
                fps_history.append(1.0 / dt)
                if len(fps_history) > 15:
                    fps_history.pop(0)
                current_fps = round(sum(fps_history) / len(fps_history), 1)

            event_bus.publish("on_camera_fps", fps=current_fps)

    def _draw_overlay(self, frame: np.ndarray, engine_result: Dict[str, Any], fps: float = 0.0):
        g_id = engine_result.get("gesture", "unknown")
        conf = engine_result.get("confidence", 0)
        stab = engine_result.get("stability", 0)
        consecutive = engine_result.get("consecutive", 0)
        req_frames = engine_result.get("required_frames", 8)

        profile = config_manager.get_active_profile()
        g_cfg = profile.gestures.get(g_id)
        icon = g_cfg.icon if g_cfg else "🖐️"
        name = g_cfg.custom_name if g_cfg else (g_id.upper() if g_id != "unknown" else "SEM GESTO")

        h, w, _ = frame.shape
        overlay = frame.copy()

        # Caixa semi-transparente no canto superior esquerdo
        cv2.rectangle(overlay, (15, 15), (340, 105), (20, 20, 30), -1)
        cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)
        cv2.rectangle(frame, (15, 15), (340, 105), (100, 100, 120), 1)

        # Exibir FPS no canto superior direito do card de overlay
        if fps > 0:
            cv2.putText(frame, f"FPS: {fps:.1f}", (245, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (140, 240, 140), 1, cv2.LINE_AA)

        if g_id != "unknown":
            color = (140, 240, 140) if consecutive >= req_frames else (230, 210, 100)
            cv2.putText(frame, f"Gesto: {name}", (30, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2, cv2.LINE_AA)
            cv2.putText(frame, f"Confianca: {conf}%", (30, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (220, 220, 220), 1, cv2.LINE_AA)
            
            # Barra de estabilidade
            bar_w = int(100 * (stab / 100.0))
            cv2.rectangle(frame, (180, 58), (280, 70), (50, 50, 60), -1)
            cv2.rectangle(frame, (180, 58), (180 + bar_w, 70), (140, 240, 140), -1)
            cv2.rectangle(frame, (180, 58), (280, 70), (180, 180, 180), 1)
            
            # Progresso dos frames de confirmação
            frame_str = f"Progresso: {consecutive}/{req_frames}"
            cv2.putText(frame, frame_str, (30, 93), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (180, 220, 255), 1, cv2.LINE_AA)
        else:
            cv2.putText(frame, "Aguardando Gesto...", (30, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (180, 180, 190), 2, cv2.LINE_AA)

camera_handler = CameraHandler()
