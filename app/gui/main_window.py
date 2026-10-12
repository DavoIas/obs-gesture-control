import os
import cv2
import threading
import queue
from PIL import Image, ImageTk
import customtkinter as ctk
from typing import Optional, Dict, Any

from app.config.manager import config_manager
from app.obs.controller import obs_controller
from app.obs.discovery import obs_discovery
from app.obs.actions import ActionExecutor
from app.vision.camera import camera_handler
from app.vision.calibration import GestureCalibrator
from app.vision.gesture_engine import gesture_engine
from app.core.logger import logger
from app.core.events import event_bus

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class GestureEditDialog(ctk.CTkToplevel):
    """
    Modal de edição completa do gesto.
    Permite alterar nome, descrição, tipo de ação, parâmetros (cenas/fontes descobertas do OBS),
    cooldown, sensibilidade, número de frames de confirmação e status.
    """
    def __init__(self, parent, gesture_id: str, on_save_callback):
        super().__init__(parent)
        self.gesture_id = gesture_id
        self.on_save_callback = on_save_callback

        profile = config_manager.get_active_profile()
        self.gesture_cfg = profile.gestures[gesture_id]
        self.action_cfg = self.gesture_cfg.action

        self.title(f"Editar Gesto - {self.gesture_cfg.icon} {self.gesture_cfg.default_name}")
        self.geometry("560x680")
        self.resizable(False, False)
        self.grab_set()

        self._build_ui()

    def _build_ui(self):
        scroll = ctk.CTkScrollableFrame(self, width=530, height=600)
        scroll.pack(padx=15, pady=15, fill="both", expand=True)

        # Cabeçalho
        lbl_head = ctk.CTkLabel(
            scroll,
            text=f"{self.gesture_cfg.icon} {self.gesture_cfg.default_name}",
            font=ctk.CTkFont(size=22, weight="bold")
        )
        lbl_head.pack(anchor="w", pady=(0, 10))

        # Nome Personalizado
        ctk.CTkLabel(scroll, text="Nome do Gesto:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(5, 2))
        self.entry_name = ctk.CTkEntry(scroll, width=500)
        self.entry_name.insert(0, self.gesture_cfg.custom_name)
        self.entry_name.pack(anchor="w", pady=(0, 10))

        # Descrição
        ctk.CTkLabel(scroll, text="Descrição:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(5, 2))
        self.entry_desc = ctk.CTkEntry(scroll, width=500)
        self.entry_desc.insert(0, self.gesture_cfg.description)
        self.entry_desc.pack(anchor="w", pady=(0, 10))

        # Status Ativado/Desativado
        self.switch_active = ctk.CTkSwitch(scroll, text="Gesto Ativado no Sistema")
        if self.gesture_cfg.active:
            self.switch_active.select()
        self.switch_active.pack(anchor="w", pady=(5, 15))

        # Divisor
        ctk.CTkFrame(scroll, height=2, fg_color="gray30").pack(fill="x", pady=10)

        # Seleção de Ação
        ctk.CTkLabel(scroll, text="Ação a Executar:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(5, 2))

        self.action_types_map = {
            "Trocar cena do OBS": "switch_scene",
            "Ativar fonte": "enable_source",
            "Desativar fonte": "disable_source",
            "Alternar fonte (ON/OFF)": "toggle_source",
            "Iniciar transmissão": "start_stream",
            "Parar transmissão": "stop_stream",
            "Iniciar gravação": "start_record",
            "Parar gravação": "stop_record",
            "Pausar gravação": "pause_record",
            "Retomar gravação": "resume_record",
            "Alternar pausa da gravação": "toggle_record_pause",
            "Alterar volume de fonte": "set_volume",
            "Mutar fonte": "mute_source",
            "Desmutar fonte": "unmute_source",
            "Alternar mute": "toggle_mute",
            "Comando personalizado (SO)": "custom_command"
        }
        self.rev_action_types = {v: k for k, v in self.action_types_map.items()}

        current_action_label = self.rev_action_types.get(self.action_cfg.action_type, "Trocar cena do OBS")
        self.combo_action = ctk.CTkOptionMenu(
            scroll,
            values=list(self.action_types_map.keys()),
            command=self._on_action_type_changed,
            width=500
        )
        self.combo_action.set(current_action_label)
        self.combo_action.pack(anchor="w", pady=(0, 10))

        # Frame de parâmetros dinâmicos
        self.frame_params = ctk.CTkFrame(scroll, fg_color="transparent")
        self.frame_params.pack(fill="x", pady=5)

        # Checkbox "Exigir confirmação" (B5)
        self.chk_confirm = ctk.CTkCheckBox(scroll, text="Exigir confirmação antes de executar")
        # TODO(decisão): Default True para stop_stream, stop_record e custom_command, respeitando valor salvo se já configurado
        initial_act_key = self.action_cfg.action_type
        if self.action_cfg.confirm_required or (initial_act_key in ["stop_stream", "stop_record", "custom_command"] and getattr(self.action_cfg, 'confirm_required', None) is not False):
            if self.action_cfg.confirm_required:
                self.chk_confirm.select()
            elif initial_act_key in ["stop_stream", "stop_record", "custom_command"]:
                self.chk_confirm.select()
            else:
                self.chk_confirm.deselect()
        else:
            self.chk_confirm.deselect()
        self.chk_confirm.pack(anchor="w", pady=(5, 10))

        # Sliders e Parâmetros Numéricos
        ctk.CTkLabel(scroll, text="Cooldown (segundos):", font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(10, 2))
        self.slider_cooldown = ctk.CTkSlider(scroll, from_=0.2, to=5.0, number_of_steps=48, width=500)
        self.slider_cooldown.set(self.gesture_cfg.cooldown)
        self.slider_cooldown.pack(anchor="w")
        self.lbl_cooldown_val = ctk.CTkLabel(scroll, text=f"{self.gesture_cfg.cooldown:.1f} segundos")
        self.lbl_cooldown_val.pack(anchor="w", pady=(0, 10))
        self.slider_cooldown.configure(command=lambda val: self.lbl_cooldown_val.configure(text=f"{val:.1f} segundos"))

        ctk.CTkLabel(scroll, text="Frames de Confirmação:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(5, 2))
        self.slider_frames = ctk.CTkSlider(scroll, from_=2, to=20, number_of_steps=18, width=500)
        self.slider_frames.set(self.gesture_cfg.required_frames)
        self.slider_frames.pack(anchor="w")
        self.lbl_frames_val = ctk.CTkLabel(scroll, text=f"{int(self.gesture_cfg.required_frames)} frames")
        self.lbl_frames_val.pack(anchor="w", pady=(0, 10))
        self.slider_frames.configure(command=lambda val: self.lbl_frames_val.configure(text=f"{int(val)} frames"))

        ctk.CTkLabel(scroll, text="Sensibilidade (%):", font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(5, 2))
        self.slider_sens = ctk.CTkSlider(scroll, from_=50, to=95, number_of_steps=45, width=500)
        self.slider_sens.set(self.gesture_cfg.sensitivity)
        self.slider_sens.pack(anchor="w")
        self.lbl_sens_val = ctk.CTkLabel(scroll, text=f"{int(self.gesture_cfg.sensitivity)} %")
        self.lbl_sens_val.pack(anchor="w", pady=(0, 10))
        self.slider_sens.configure(command=lambda val: self.lbl_sens_val.configure(text=f"{int(val)} %"))

        # Botões de Ação
        btn_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        btn_frame.pack(fill="x", pady=20)

        btn_test = ctk.CTkButton(btn_frame, text="🧪 Testar Ação Agora", fg_color="gray40", hover_color="gray30", command=self._test_action)
        btn_test.pack(side="left", padx=(0, 10))

        btn_save = ctk.CTkButton(btn_frame, text="💾 Salvar Alterações", fg_color="#2b8a3e", hover_color="#237032", command=self._save)
        btn_save.pack(side="right")

        self._render_dynamic_params()

    def _on_action_type_changed(self, choice):
        self._render_dynamic_params()
        act_key = self.action_types_map.get(choice, "switch_scene")
        if hasattr(self, 'chk_confirm'):
            if act_key in ["stop_stream", "stop_record", "custom_command"]:
                self.chk_confirm.select()
            else:
                self.chk_confirm.deselect()

    def _render_dynamic_params(self):
        for widget in self.frame_params.winfo_children():
            widget.destroy()

        selected_label = self.combo_action.get()
        act_key = self.action_types_map.get(selected_label, "switch_scene")

        scenes = obs_discovery.get_scenes()
        sources = obs_discovery.get_sources()

        scene_values = scenes if scenes else ["Conecte ao OBS para listar cenas"]

        if act_key in ["switch_scene", "enable_source", "disable_source", "toggle_source"]:
            ctk.CTkLabel(self.frame_params, text="Cena:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(5, 2))
            self.combo_scene = ctk.CTkComboBox(self.frame_params, values=scene_values, width=500, command=self._on_scene_selected)
            if self.action_cfg.scene_name:
                self.combo_scene.set(self.action_cfg.scene_name)
            elif scenes:
                self.combo_scene.set(scenes[0])
            else:
                self.combo_scene.set("")
            self.combo_scene.pack(anchor="w", pady=(0, 10))

        if act_key in ["enable_source", "disable_source", "toggle_source", "set_volume", "mute_source", "unmute_source", "toggle_mute"]:
            ctk.CTkLabel(self.frame_params, text="Fonte:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(5, 2))
            
            # Para ações de cena, filtra as fontes pela cena selecionada (T6)
            current_scene = self.combo_scene.get() if hasattr(self, 'combo_scene') else ""
            if act_key in ["enable_source", "disable_source", "toggle_source"] and current_scene and current_scene != "Conecte ao OBS para listar cenas":
                scene_sources = obs_discovery.get_scene_sources(current_scene)
                active_sources = scene_sources if scene_sources else sources
            else:
                active_sources = sources

            src_values = active_sources if active_sources else ["Conecte ao OBS para listar fontes"]
            self.combo_source = ctk.CTkComboBox(self.frame_params, values=src_values, width=500)
            if self.action_cfg.source_name:
                self.combo_source.set(self.action_cfg.source_name)
            elif active_sources:
                self.combo_source.set(active_sources[0])
            else:
                self.combo_source.set("")
            self.combo_source.pack(anchor="w", pady=(0, 10))

        if act_key == "set_volume":
            ctk.CTkLabel(self.frame_params, text="Volume (dB):", font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(5, 2))
            self.entry_vol = ctk.CTkEntry(self.frame_params, width=500)
            self.entry_vol.insert(0, str(self.action_cfg.volume_db))
            self.entry_vol.pack(anchor="w", pady=(0, 10))

        if act_key == "custom_command":
            ctk.CTkLabel(self.frame_params, text="Comando do Sistema Operacional:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(5, 2))
            self.entry_cmd = ctk.CTkEntry(self.frame_params, width=500, placeholder_text="Ex: notepad.exe ou calc")
            self.entry_cmd.insert(0, self.action_cfg.command_str)
            self.entry_cmd.pack(anchor="w", pady=(0, 10))

    def _on_scene_selected(self, selected_scene: str):
        if hasattr(self, 'combo_source') and self.combo_source:
            act_key = self.action_types_map.get(self.combo_action.get(), "switch_scene")
            if act_key in ["enable_source", "disable_source", "toggle_source"]:
                if selected_scene and selected_scene != "Conecte ao OBS para listar cenas":
                    sources = obs_discovery.get_scene_sources(selected_scene)
                    if not sources:
                        sources = obs_discovery.get_sources()
                    vals = sources if sources else ["Conecte ao OBS para listar fontes"]
                    self.combo_source.configure(values=vals)
                    current_val = self.combo_source.get()
                    if sources and current_val not in sources:
                        self.combo_source.set(sources[0])

    def _test_action(self):
        act_key = self.action_types_map.get(self.combo_action.get(), "switch_scene")
        test_act = self._build_action_config_from_form(act_key)
        ActionExecutor.submit(test_act, gesture_name=self.entry_name.get())

    def _build_action_config_from_form(self, act_key: str):
        scene_val = getattr(self, 'combo_scene', None)
        scene_name = scene_val.get().strip() if scene_val else ""
        if scene_name == "Conecte ao OBS para listar cenas":
            scene_name = ""

        source_val = getattr(self, 'combo_source', None)
        source_name = source_val.get().strip() if source_val else ""
        if source_name == "Conecte ao OBS para listar fontes":
            source_name = ""

        vol_val = getattr(self, 'entry_vol', None)
        try:
            volume_db = float(vol_val.get()) if vol_val and vol_val.get() else 0.0
        except ValueError:
            volume_db = 0.0

        cmd_val = getattr(self, 'entry_cmd', None)
        cmd_str = cmd_val.get() if cmd_val else ""

        confirm_req = bool(self.chk_confirm.get()) if hasattr(self, 'chk_confirm') else (act_key in ["stop_stream", "stop_record", "custom_command"])

        return self.action_cfg.__class__(
            action_type=act_key,
            scene_name=scene_name,
            source_name=source_name,
            volume_db=volume_db,
            command_str=cmd_str,
            confirm_required=confirm_req
        )

    def _save(self):
        act_key = self.action_types_map.get(self.combo_action.get(), "switch_scene")
        new_action = self._build_action_config_from_form(act_key)

        self.gesture_cfg.custom_name = self.entry_name.get()
        self.gesture_cfg.description = self.entry_desc.get()
        self.gesture_cfg.active = bool(self.switch_active.get())
        self.gesture_cfg.cooldown = round(self.slider_cooldown.get(), 1)
        self.gesture_cfg.required_frames = int(self.slider_frames.get())
        self.gesture_cfg.sensitivity = int(self.slider_sens.get())
        self.gesture_cfg.action = new_action

        config_manager.update_gesture(self.gesture_id, self.gesture_cfg)
        self.on_save_callback()
        self.destroy()


class MainWindow(ctk.CTk):
    """
    Interface Gráfica de Usuário Principal moderna e modular (OBS Gesture Control V2).
    """
    def __init__(self):
        super().__init__()

        self.title("OBS Gesture Control V2 - Sistema de Controle por Gestos")
        self.geometry("1100x720")
        self.minsize(980, 650)

        self.current_page = "dashboard"
        self.calibrator: Optional[GestureCalibrator] = None
        self._calibrator_lock = threading.Lock()

        # Fila thread-safe de atualizações da interface e controle de frames de vídeo (T3)
        self._ui_queue: queue.Queue = queue.Queue()
        self._latest_video_frame = None
        self._video_frame_lock = threading.Lock()

        self._build_layout()
        self._subscribe_events()

        # Iniciar consumo periódico da fila de UI na thread principal
        self.after(15, self._drain_ui_queue)

        # Iniciar Câmera e Tentar Conexão OBS ao iniciar
        if config_manager.config.obs.auto_connect:
            threading.Thread(target=obs_controller.connect, daemon=True).start()
        camera_handler.start()
        camera_handler.add_on_frame_listener(self._on_camera_frame)

    def _drain_ui_queue(self):
        try:
            # Processa callbacks pendentes da UI
            count = 0
            while not self._ui_queue.empty() and count < 60:
                cb = self._ui_queue.get_nowait()
                try:
                    cb()
                except Exception as e:
                    logger.log(f"Erro em callback de UI: {e}", "ERROR")
                count += 1

            # Processa o último frame de vídeo recebido (evita fila acumulada)
            with self._video_frame_lock:
                frame = self._latest_video_frame
                self._latest_video_frame = None

            if frame is not None and self.current_page == "dashboard" and hasattr(self, 'video_label'):
                try:
                    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    img = Image.fromarray(rgb)
                    img = img.resize((540, 320), Image.Resampling.LANCZOS)
                    ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(540, 320))
                    self.video_label.configure(image=ctk_img, text="")
                except Exception:
                    pass
        finally:
            try:
                self.after(15, self._drain_ui_queue)
            except Exception:
                pass

    def _build_layout(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # 1. MENU LATERAL (Sidebar)
        self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")

        lbl_logo = ctk.CTkLabel(
            self.sidebar,
            text="🖐️ OBS Gesture V2",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        lbl_logo.pack(padx=20, pady=(20, 20))

        self.btn_nav_dashboard = ctk.CTkButton(self.sidebar, text="📊 Dashboard", anchor="w", command=lambda: self.show_page("dashboard"))
        self.btn_nav_dashboard.pack(fill="x", padx=10, pady=4)

        self.btn_nav_gestures = ctk.CTkButton(self.sidebar, text="✌️ Gestos (8/8)", anchor="w", command=lambda: self.show_page("gestures"))
        self.btn_nav_gestures.pack(fill="x", padx=10, pady=4)

        self.btn_nav_profiles = ctk.CTkButton(self.sidebar, text="👤 Perfis", anchor="w", command=lambda: self.show_page("profiles"))
        self.btn_nav_profiles.pack(fill="x", padx=10, pady=4)

        self.btn_nav_obs = ctk.CTkButton(self.sidebar, text="🎥 OBS Studio", anchor="w", command=lambda: self.show_page("obs"))
        self.btn_nav_obs.pack(fill="x", padx=10, pady=4)

        self.btn_nav_camera = ctk.CTkButton(self.sidebar, text="📷 Câmera", anchor="w", command=lambda: self.show_page("camera"))
        self.btn_nav_camera.pack(fill="x", padx=10, pady=4)

        self.btn_nav_calibration = ctk.CTkButton(self.sidebar, text="🎯 Calibração", anchor="w", command=lambda: self.show_page("calibration"))
        self.btn_nav_calibration.pack(fill="x", padx=10, pady=4)

        self.btn_nav_logs = ctk.CTkButton(self.sidebar, text="📝 Logs", anchor="w", command=lambda: self.show_page("logs"))
        self.btn_nav_logs.pack(fill="x", padx=10, pady=4)

        self.btn_nav_settings = ctk.CTkButton(self.sidebar, text="⚙️ Configurações", anchor="w", command=lambda: self.show_page("settings"))
        self.btn_nav_settings.pack(fill="x", padx=10, pady=4)

        # Rodapé da sidebar
        lbl_ver = ctk.CTkLabel(self.sidebar, text="Versão 2.0 (Zero-Code)", font=ctk.CTkFont(size=11), text_color="gray60")
        lbl_ver.pack(side="bottom", pady=15)

        # 2. ÁREA DE CONTEÚDO PRINCIPAL
        self.main_container = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.main_container.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.main_container.grid_rowconfigure(0, weight=1)
        self.main_container.grid_columnconfigure(0, weight=1)

        self.pages: Dict[str, ctk.CTkFrame] = {}
        self._init_pages()
        self.show_page("dashboard")

    def _init_pages(self):
        self._build_dashboard_page()
        self._build_gestures_page()
        self._build_profiles_page()
        self._build_obs_page()
        self._build_camera_page()
        self._build_calibration_page()
        self._build_logs_page()
        self._build_settings_page()

    def show_page(self, page_name: str):
        self.current_page = page_name
        for name, frame in self.pages.items():
            if name == page_name:
                frame.grid(row=0, column=0, sticky="nsew")
            else:
                frame.grid_forget()

    # ==================== PAGE BUILDERS ====================

    def _build_dashboard_page(self):
        page = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.pages["dashboard"] = page

        # Cards Topo Status
        top_cards = ctk.CTkFrame(page, fg_color="transparent")
        top_cards.pack(fill="x", pady=(0, 15))

        self.card_obs_status = ctk.CTkFrame(top_cards, width=220, height=75)
        self.card_obs_status.pack(side="left", padx=(0, 10))
        self.lbl_obs_icon = ctk.CTkLabel(self.card_obs_status, text="🔴 OBS Desconectado", font=ctk.CTkFont(size=14, weight="bold"))
        self.lbl_obs_icon.pack(padx=15, pady=20)

        self.card_cam_status = ctk.CTkFrame(top_cards, width=220, height=75)
        self.card_cam_status.pack(side="left", padx=(0, 10))
        self.lbl_cam_icon = ctk.CTkLabel(self.card_cam_status, text="🟢 Câmera Ativa", font=ctk.CTkFont(size=14, weight="bold"))
        self.lbl_cam_icon.pack(padx=15, pady=20)

        # Card de FPS Real (T5)
        self.card_fps = ctk.CTkFrame(top_cards, width=150, height=75)
        self.card_fps.pack(side="left", padx=(0, 10))
        self.lbl_fps_val = ctk.CTkLabel(self.card_fps, text="⚡ FPS: --", font=ctk.CTkFont(size=14, weight="bold"))
        self.lbl_fps_val.pack(padx=15, pady=20)

        # Toggle Modo Teste
        self.switch_test_mode = ctk.CTkSwitch(
            top_cards, text="[ MODO TESTE ]", font=ctk.CTkFont(weight="bold"),
            command=self._toggle_test_mode
        )
        if config_manager.config.test_mode:
            self.switch_test_mode.select()
        self.switch_test_mode.pack(side="right", padx=10)

        # Área Central Grid (Preview Vídeo + Status do Gesto)
        center_grid = ctk.CTkFrame(page, fg_color="transparent")
        center_grid.pack(fill="both", expand=True)
        center_grid.grid_columnconfigure(0, weight=3)
        center_grid.grid_columnconfigure(1, weight=2)
        center_grid.grid_rowconfigure(0, weight=1)

        # Live Video Preview Canvas
        video_card = ctk.CTkFrame(center_grid)
        video_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        ctk.CTkLabel(video_card, text="Preview da Webcam + Overlay", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=15, pady=10)

        self.video_label = ctk.CTkLabel(video_card, text="Carregando vídeo...")
        self.video_label.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        # Status Gesto Ativo Card
        gesture_card = ctk.CTkFrame(center_grid)
        gesture_card.grid(row=0, column=1, sticky="nsew")

        ctk.CTkLabel(gesture_card, text="Painel de Monitoramento", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", padx=15, pady=10)

        self.lbl_active_gesture = ctk.CTkLabel(gesture_card, text="✌️ SEM GESTO", font=ctk.CTkFont(size=24, weight="bold"))
        self.lbl_active_gesture.pack(pady=(20, 5))

        ctk.CTkLabel(gesture_card, text="Confiança:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=20, pady=(10, 2))
        self.lbl_conf_pct = ctk.CTkLabel(gesture_card, text="0 %", font=ctk.CTkFont(size=16))
        self.lbl_conf_pct.pack(anchor="w", padx=20)

        ctk.CTkLabel(gesture_card, text="Estabilidade:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=20, pady=(10, 2))
        self.progress_stability = ctk.CTkProgressBar(gesture_card, width=250)
        self.progress_stability.set(0.0)
        self.progress_stability.pack(anchor="w", padx=20, pady=2)

        ctk.CTkLabel(gesture_card, text="Última Ação Disparada:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=20, pady=(20, 2))
        self.lbl_last_action = ctk.CTkLabel(gesture_card, text="Nenhuma ação disparada ainda.", text_color="gray70", wraplength=260)
        self.lbl_last_action.pack(anchor="w", padx=20)

    def _build_gestures_page(self):
        page = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.pages["gestures"] = page

        ctk.CTkLabel(page, text="Gestos Pré-definidos do Sistema (8/8)", font=ctk.CTkFont(size=20, weight="bold")).pack(anchor="w", pady=(0, 15))

        self.scroll_gestures = ctk.CTkScrollableFrame(page)
        self.scroll_gestures.pack(fill="both", expand=True)

        self._refresh_gestures_list()

    def _refresh_gestures_list(self):
        for widget in self.scroll_gestures.winfo_children():
            widget.destroy()

        profile = config_manager.get_active_profile()

        for g_id, g_cfg in profile.gestures.items():
            card = ctk.CTkFrame(self.scroll_gestures)
            card.pack(fill="x", padx=10, pady=6)

            left_frame = ctk.CTkFrame(card, fg_color="transparent")
            left_frame.pack(side="left", padx=15, pady=10)

            lbl_icon = ctk.CTkLabel(left_frame, text=f"{g_cfg.icon}  {g_cfg.custom_name}", font=ctk.CTkFont(size=16, weight="bold"))
            lbl_icon.pack(anchor="w")

            act_type_str = g_cfg.action.action_type
            act_param_str = g_cfg.action.scene_name or g_cfg.action.source_name or g_cfg.action.command_str
            desc_text = f"Ação: {act_type_str} {f'({act_param_str})' if act_param_str else ''}"
            lbl_desc = ctk.CTkLabel(left_frame, text=desc_text, text_color="gray70")
            lbl_desc.pack(anchor="w")

            right_frame = ctk.CTkFrame(card, fg_color="transparent")
            right_frame.pack(side="right", padx=15, pady=10)

            status_color = "#2b8a3e" if g_cfg.active else "gray50"
            status_text = "ATIVO" if g_cfg.active else "INATIVO"
            lbl_st = ctk.CTkLabel(right_frame, text=status_text, text_color=status_color, font=ctk.CTkFont(weight="bold"))
            lbl_st.pack(side="left", padx=10)

            btn_test = ctk.CTkButton(
                right_frame, text="🧪 Testar", width=80, fg_color="gray40", hover_color="gray30",
                command=lambda id=g_id: ActionExecutor.execute(profile.gestures[id].action, gesture_name=profile.gestures[id].custom_name)
            )
            btn_test.pack(side="left", padx=5)

            btn_edit = ctk.CTkButton(
                right_frame, text="✏️ Editar", width=80,
                command=lambda id=g_id: GestureEditDialog(self, id, self._refresh_gestures_list)
            )
            btn_edit.pack(side="left", padx=5)

    def _build_profiles_page(self):
        page = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.pages["profiles"] = page

        ctk.CTkLabel(page, text="Gerenciador de Perfis", font=ctk.CTkFont(size=20, weight="bold")).pack(anchor="w", pady=(0, 15))

        top_bar = ctk.CTkFrame(page, fg_color="transparent")
        top_bar.pack(fill="x", pady=(0, 15))

        ctk.CTkLabel(top_bar, text="Perfil Ativo:", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=(0, 10))

        profiles_list = list(config_manager.config.profiles.keys())
        self.combo_profiles = ctk.CTkOptionMenu(
            top_bar, values=profiles_list, command=self._on_profile_switched, width=220
        )
        self.combo_profiles.set(config_manager.config.active_profile)
        self.combo_profiles.pack(side="left", padx=(0, 15))

        btn_new_p = ctk.CTkButton(top_bar, text="➕ Novo Perfil", command=self._create_new_profile)
        btn_new_p.pack(side="left", padx=5)

        btn_dup_p = ctk.CTkButton(top_bar, text="📋 Duplicar Perfil", fg_color="gray40", command=self._duplicate_profile)
        btn_dup_p.pack(side="left", padx=5)

        btn_del_p = ctk.CTkButton(top_bar, text="🗑️ Excluir Perfil", fg_color="#c92a2a", hover_color="#a61e1e", command=self._delete_profile)
        btn_del_p.pack(side="left", padx=5)

        self.scroll_profiles = ctk.CTkScrollableFrame(page)
        self.scroll_profiles.pack(fill="both", expand=True)

        self._refresh_profiles_list()

    def _refresh_profiles_list(self):
        for w in self.scroll_profiles.winfo_children():
            w.destroy()

        for p_name, p_cfg in config_manager.config.profiles.items():
            card = ctk.CTkFrame(self.scroll_profiles)
            card.pack(fill="x", padx=10, pady=8)

            lbl_title = ctk.CTkLabel(card, text=f"👤 {p_name}", font=ctk.CTkFont(size=16, weight="bold"))
            lbl_title.pack(anchor="w", padx=15, pady=(10, 2))

            lbl_desc = ctk.CTkLabel(card, text=p_cfg.description or "Sem descrição", text_color="gray70")
            lbl_desc.pack(anchor="w", padx=15, pady=(0, 10))

    def _on_profile_switched(self, choice):
        config_manager.set_active_profile(choice)
        self._refresh_gestures_list()

    def _create_new_profile(self):
        dialog = ctk.CTkInputDialog(text="Digite o nome do novo perfil:", title="Novo Perfil")
        name = dialog.get_input()
        if name:
            if config_manager.create_profile(name):
                self.combo_profiles.configure(values=list(config_manager.config.profiles.keys()))
                self.combo_profiles.set(name)
                self._refresh_profiles_list()
                self._refresh_gestures_list()

    def _duplicate_profile(self):
        curr = config_manager.config.active_profile
        dialog = ctk.CTkInputDialog(text=f"Digite o nome da cópia de '{curr}':", title="Duplicar Perfil")
        name = dialog.get_input()
        if name:
            if config_manager.create_profile(name, copy_from=curr):
                self.combo_profiles.configure(values=list(config_manager.config.profiles.keys()))
                self.combo_profiles.set(name)
                self._refresh_profiles_list()
                self._refresh_gestures_list()

    def _delete_profile(self):
        curr = config_manager.config.active_profile
        if len(config_manager.config.profiles) <= 1:
            return
        if config_manager.delete_profile(curr):
            self.combo_profiles.configure(values=list(config_manager.config.profiles.keys()))
            self.combo_profiles.set(config_manager.config.active_profile)
            self._refresh_profiles_list()
            self._refresh_gestures_list()

    def _build_obs_page(self):
        page = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.pages["obs"] = page

        ctk.CTkLabel(page, text="Configuração do OBS Studio (WebSocket 5.x)", font=ctk.CTkFont(size=20, weight="bold")).pack(anchor="w", pady=(0, 15))

        cfg_frame = ctk.CTkFrame(page)
        cfg_frame.pack(fill="x", pady=(0, 15), padx=5)

        ctk.CTkLabel(cfg_frame, text="Endereço Host:").grid(row=0, column=0, padx=15, pady=10, sticky="w")
        self.entry_obs_host = ctk.CTkEntry(cfg_frame, width=200)
        self.entry_obs_host.insert(0, config_manager.config.obs.host)
        self.entry_obs_host.grid(row=0, column=1, padx=15, pady=10)

        ctk.CTkLabel(cfg_frame, text="Porta WebSocket:").grid(row=0, column=2, padx=15, pady=10, sticky="w")
        self.entry_obs_port = ctk.CTkEntry(cfg_frame, width=120)
        self.entry_obs_port.insert(0, str(config_manager.config.obs.port))
        self.entry_obs_port.grid(row=0, column=3, padx=15, pady=10)

        ctk.CTkLabel(cfg_frame, text="Senha:").grid(row=1, column=0, padx=15, pady=10, sticky="w")
        self.entry_obs_pass = ctk.CTkEntry(cfg_frame, width=200, show="*")
        self.entry_obs_pass.insert(0, config_manager.config.obs.password)
        self.entry_obs_pass.grid(row=1, column=1, padx=15, pady=10)

        btn_conn = ctk.CTkButton(cfg_frame, text="⚡ Conectar Agora", command=self._connect_obs)
        btn_conn.grid(row=1, column=2, columnspan=2, padx=15, pady=10, sticky="ew")

        # Seção de Descoberta Automática
        disc_frame = ctk.CTkFrame(page)
        disc_frame.pack(fill="both", expand=True, padx=5, pady=5)

        disc_header = ctk.CTkFrame(disc_frame, fg_color="transparent")
        disc_header.pack(fill="x", padx=15, pady=10)
        ctk.CTkLabel(disc_header, text="Cenas e Fontes Descobertas Automaticamente", font=ctk.CTkFont(size=16, weight="bold")).pack(side="left")

        btn_ref = ctk.CTkButton(disc_header, text="🔄 Atualizar Descoberta", width=160, command=lambda: obs_discovery.refresh())
        btn_ref.pack(side="right")

        disc_scroll = ctk.CTkScrollableFrame(disc_frame)
        disc_scroll.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        self.lbl_obs_discovery_list = ctk.CTkLabel(disc_scroll, text="Conecte ao OBS para listar cenas e fontes.", justify="left")
        self.lbl_obs_discovery_list.pack(anchor="w", padx=10, pady=10)

    def _connect_obs(self):
        obs_cfg = config_manager.config.obs
        obs_cfg.host = self.entry_obs_host.get()
        obs_cfg.port = int(self.entry_obs_port.get() or 4455)
        obs_cfg.password = self.entry_obs_pass.get()
        config_manager.save()

        threading.Thread(target=obs_controller.connect, daemon=True).start()

    def _build_camera_page(self):
        page = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.pages["camera"] = page

        ctk.CTkLabel(page, text="Configurações da Câmera e Visão Computacional", font=ctk.CTkFont(size=20, weight="bold")).pack(anchor="w", pady=(0, 15))

        cam_frame = ctk.CTkFrame(page)
        cam_frame.pack(fill="x", pady=10)

        ctk.CTkLabel(cam_frame, text="Índice da Câmera (Dispositivo):", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=15, pady=(15, 2))
        self.combo_cam_idx = ctk.CTkOptionMenu(cam_frame, values=["0", "1", "2", "3"], command=self._on_cam_index_changed)
        self.combo_cam_idx.set(str(config_manager.config.camera.device_index))
        self.combo_cam_idx.pack(anchor="w", padx=15, pady=(0, 15))

        self.switch_landmarks = ctk.CTkSwitch(cam_frame, text="Desenhar Esqueleto da Mão (Landmarks 3D)", command=self._toggle_landmarks)
        if config_manager.config.camera.draw_landmarks:
            self.switch_landmarks.select()
        self.switch_landmarks.pack(anchor="w", padx=15, pady=10)

        self.switch_overlay = ctk.CTkSwitch(cam_frame, text="Desenhar Painel Overlay no Vídeo", command=self._toggle_overlay)
        if config_manager.config.camera.draw_overlay:
            self.switch_overlay.select()
        self.switch_overlay.pack(anchor="w", padx=15, pady=(10, 15))

    def _on_cam_index_changed(self, choice):
        config_manager.config.camera.device_index = int(choice)
        config_manager.save()
        camera_handler.stop()
        camera_handler.start()

    def _toggle_landmarks(self):
        config_manager.config.camera.draw_landmarks = bool(self.switch_landmarks.get())
        config_manager.save()

    def _toggle_overlay(self):
        config_manager.config.camera.draw_overlay = bool(self.switch_overlay.get())
        config_manager.save()

    def _build_calibration_page(self):
        page = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.pages["calibration"] = page

        ctk.CTkLabel(page, text="Ferramenta de Calibração de Gestos", font=ctk.CTkFont(size=20, weight="bold")).pack(anchor="w", pady=(0, 15))

        card = ctk.CTkFrame(page)
        card.pack(fill="x", pady=10)

        ctk.CTkLabel(card, text="Selecione o gesto para calibrar:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=15, pady=(15, 2))
        gestures_keys = list(config_manager.get_active_profile().gestures.keys())
        self.combo_calib_g = ctk.CTkOptionMenu(card, values=gestures_keys)
        self.combo_calib_g.pack(anchor="w", padx=15, pady=(0, 15))

        btn_start_calib = ctk.CTkButton(card, text="🎯 Iniciar Calibração (30 Frames)", command=self._start_calibration)
        btn_start_calib.pack(anchor="w", padx=15, pady=(0, 15))

        self.progress_calib = ctk.CTkProgressBar(card, width=400)
        self.progress_calib.set(0.0)
        self.progress_calib.pack(anchor="w", padx=15, pady=10)

        self.lbl_calib_result = ctk.CTkLabel(card, text="Clique em Iniciar para calibrar o enquadramento e contraste da mão.", wraplength=500)
        self.lbl_calib_result.pack(anchor="w", padx=15, pady=(10, 15))

    def _start_calibration(self):
        target = self.combo_calib_g.get()
        with self._calibrator_lock:
            self.calibrator = GestureCalibrator(target_gesture=target, sample_goal=30)
        self.lbl_calib_result.configure(text="Faça o gesto diante da câmera agora...")

    def _build_logs_page(self):
        page = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.pages["logs"] = page

        top = ctk.CTkFrame(page, fg_color="transparent")
        top.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(top, text="Logs do Sistema em Tempo Real", font=ctk.CTkFont(size=20, weight="bold")).pack(side="left")

        btn_clr = ctk.CTkButton(top, text="🗑️ Limpar Logs", width=120, command=lambda: logger.clear())
        btn_clr.pack(side="right")

        self.textbox_logs = ctk.CTkTextbox(page, width=700, height=450, font=ctk.CTkFont(family="Consolas", size=12))
        self.textbox_logs.pack(fill="both", expand=True)

    def _build_settings_page(self):
        page = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.pages["settings"] = page

        ctk.CTkLabel(page, text="Configurações Gerais do Sistema", font=ctk.CTkFont(size=20, weight="bold")).pack(anchor="w", pady=(0, 15))

        card = ctk.CTkFrame(page)
        card.pack(fill="x", pady=10)

        self.switch_confirm_dest = ctk.CTkSwitch(
            card, text="Exigir Confirmação para Ações Destrutivas (Parar Stream / Gravação)",
            command=self._save_general_settings
        )
        if config_manager.config.confirm_destructive_actions:
            self.switch_confirm_dest.select()
        self.switch_confirm_dest.pack(anchor="w", padx=15, pady=15)

    def _save_general_settings(self):
        config_manager.config.confirm_destructive_actions = bool(self.switch_confirm_dest.get())
        config_manager.save()

    def _toggle_test_mode(self):
        val = bool(self.switch_test_mode.get())
        config_manager.set_test_mode(val)

    # ==================== CALLBACKS E EVENTOS ====================

    def _subscribe_events(self):
        event_bus.subscribe("on_obs_status", self._on_obs_status)
        event_bus.subscribe("on_obs_discovery_refreshed", self._on_obs_discovery)
        event_bus.subscribe("on_gesture_processed", self._on_gesture_processed)
        event_bus.subscribe("on_log_message", self._on_log_message)
        event_bus.subscribe("on_action_confirm_required", self._on_confirm_dialog)
        event_bus.subscribe("on_camera_fps", self._on_camera_fps)

    def _on_camera_fps(self, fps: float):
        def update():
            if hasattr(self, 'lbl_fps_val'):
                self.lbl_fps_val.configure(text=f"⚡ FPS: {fps:.1f}")
        self._ui_queue.put(update)

    def _on_obs_status(self, connected: bool, message: str):
        def update():
            if connected:
                self.lbl_obs_icon.configure(text="🟢 OBS Conectado", text_color="#2b8a3e")
                obs_discovery.refresh()
            else:
                self.lbl_obs_icon.configure(text="🔴 OBS Desconectado", text_color="#c92a2a")
        self._ui_queue.put(update)

    def _on_obs_discovery(self, scenes, sources):
        def update():
            text = f"Cenas Disponíveis ({len(scenes)}):\n" + "\n".join([f"  • {s}" for s in scenes]) + "\n\n"
            text += f"Fontes Disponíveis ({len(sources)}):\n" + "\n".join([f"  • {s}" for s in sources])
            self.lbl_obs_discovery_list.configure(text=text)
        self._ui_queue.put(update)

    def _on_gesture_processed(self, gesture, confidence, stability, consecutive, required_frames, triggered, action_desc):
        def update():
            if self.current_page == "dashboard":
                profile = config_manager.get_active_profile()
                g_cfg = profile.gestures.get(gesture)
                icon = g_cfg.icon if g_cfg else "🖐️"
                name = g_cfg.custom_name if g_cfg else (gesture.upper() if gesture != "unknown" else "SEM GESTO")

                self.lbl_active_gesture.configure(text=f"{icon} {name}")
                self.lbl_conf_pct.configure(text=f"{confidence} %")
                self.progress_stability.set(stability / 100.0)

                if triggered:
                    self.lbl_last_action.configure(text=action_desc or f"Gesto {name} ativado!")
        self._ui_queue.put(update)

    def _on_log_message(self, log_text, **kwargs):
        def update():
            if hasattr(self, 'textbox_logs'):
                self.textbox_logs.insert("end", log_text + "\n")
                self.textbox_logs.see("end")
        self._ui_queue.put(update)

    def _on_confirm_dialog(self, gesture, action):
        def ask():
            if getattr(self, '_confirm_dialog_open', False):
                return
            self._confirm_dialog_open = True
            gesture_engine.pending_confirmation = True

            top = ctk.CTkToplevel(self)
            top.title("Confirmação de Segurança")
            top.geometry("400x200")
            top.grab_set()

            def close_dialog():
                self._confirm_dialog_open = False
                gesture_engine.pending_confirmation = False
                try:
                    top.grab_release()
                    top.destroy()
                except Exception:
                    pass

            top.protocol("WM_DELETE_WINDOW", close_dialog)

            ctk.CTkLabel(top, text="⚠️ Ação Destrutiva Detectada", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(15, 5))
            ctk.CTkLabel(top, text=f"Gesto '{gesture}' solicitou a ação '{action.action_type}'.\nConfirma a execução?", wraplength=350).pack(pady=10)

            btn_box = ctk.CTkFrame(top, fg_color="transparent")
            btn_box.pack(pady=15)

            def on_confirm():
                close_dialog()
                ActionExecutor.submit(action, gesture)

            ctk.CTkButton(btn_box, text="Sim, Executar", fg_color="#c92a2a", command=on_confirm).pack(side="left", padx=10)
            ctk.CTkButton(btn_box, text="Cancelar", fg_color="gray40", command=close_dialog).pack(side="right", padx=10)
        self._ui_queue.put(ask)

    def _on_camera_frame(self, frame, engine_result, raw_hands):
        # Atualizar calibração se ativa (thread-safe)
        with self._calibrator_lock:
            calib = self.calibrator

        if calib and not calib.is_finished:
            if raw_hands:
                finished = calib.add_frame(raw_hands[0])
                prog = calib.get_progress()
                self._ui_queue.put(lambda p=prog: self.progress_calib.set(p) if hasattr(self, 'progress_calib') else None)
                if finished:
                    res = calib.analyze()
                    msg = f"CALIBRAÇÃO CONCLUÍDA!\nQualidade: {res['quality']}\nConfiança Média: {res['avg_confidence']}%\n\nRecomendação: {res['recommendation']}"
                    def finish_calib():
                        with self._calibrator_lock:
                            self.calibrator = None
                        if hasattr(self, 'lbl_calib_result'):
                            self.lbl_calib_result.configure(text=msg)
                    self._ui_queue.put(finish_calib)

        # Atualizar o frame mais recente para renderização na thread principal (descarta atrasados)
        if frame is not None:
            with self._video_frame_lock:
                self._latest_video_frame = frame
