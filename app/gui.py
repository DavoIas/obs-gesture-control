import tkinter as tk
from tkinter import ttk, messagebox
import cv2
from PIL import Image, ImageTk
import time
from typing import Optional, Callable
from app.config import ConfigManager
from app.obs_controller import OBSController
from app.camera import CameraHandler


# =============================================================================
# REVENUE-CENTRIC DESIGN & FRONTEND SYSTEM (helio-costa-dev / richardrx RCD)
# =============================================================================
# Principios RCD aplicados:
# 1. Informa num relance (F-Pattern: KPIs de status no topo-esquerda).
# 2. Informação com contexto (Status com rótulos explicativos, sem ambiguidades).
# 3. Design direcionado à ação (Botões primários destacados + feedback instantâneo).
# 4. Prova imediata (Overlay visual do esqueleto da mão + log temporal de ações).
# =============================================================================

COLOR_BG_DARK = "#090b10"          # Fundo Deep Cyber Space
COLOR_PANEL_BG = "#11141f"         # Fundo de painéis e cards
COLOR_PANEL_BORDER = "#1c2233"     # Bordas e divisores sutis
COLOR_CARD_HEADER = "#171c2b"      # Cabeçalho dos cards

COLOR_ACCENT_MINT = "#00f5a0"      # Verde Neon de status ativo / sucesso (RCD High Impact)
COLOR_ACCENT_CYBER = "#00b4d8"     # Azul elétrico para destaque primário
COLOR_ACCENT_PURPLE = "#7b2cbf"    # Roxo de identidade e marca
COLOR_ACCENT_AMBER = "#ffb703"     # Amarelo/Laranja de alerta e progresso
COLOR_ACCENT_CORAL = "#ff4d6d"     # Vermelho/Coral para erros/desligado

COLOR_TEXT_PRIMARY = "#f8f9fa"     # Texto principal claro
COLOR_TEXT_MUTED = "#8c9b90"       # Texto secundário
COLOR_TEXT_DARK = "#050608"        # Texto escuro para botões de alto contraste

FONT_TITLE = ("Segoe UI", 16, "bold")
FONT_SUBTITLE = ("Segoe UI", 9)
FONT_KPI_VAL = ("Segoe UI", 12, "bold")
FONT_KPI_LBL = ("Segoe UI", 8, "bold")
FONT_SECTION = ("Segoe UI", 10, "bold")
FONT_BODY = ("Segoe UI", 9)
FONT_BADGE = ("Segoe UI", 16, "bold")
FONT_BTN = ("Segoe UI", 10, "bold")


class SettingsDialog(tk.Toplevel):
    """
    Janela modal de configurações estruturada com clareza e sem atrito.
    """
    def __init__(self, parent, config_manager: ConfigManager, on_save_callback: Callable):
        super().__init__(parent)
        self.config_manager = config_manager
        self.on_save_callback = on_save_callback

        self.title("⚙️ Configurações do Sistema - OBS Gesture Control")
        self.geometry("490x580")
        self.resizable(False, False)
        self.configure(bg=COLOR_BG_DARK)
        self.transient(parent)
        self.grab_set()

        self._init_ui()

    def _init_ui(self):
        container = tk.Frame(self, bg=COLOR_BG_DARK, padx=24, pady=20)
        container.pack(fill=tk.BOTH, expand=True)

        # Cabeçalho
        title_lbl = tk.Label(
            container, text="⚙️ CONFIGURAÇÕES DO SISTEMA",
            font=FONT_TITLE, bg=COLOR_BG_DARK, fg=COLOR_ACCENT_CYBER
        )
        title_lbl.pack(anchor="w", pady=(0, 4))

        sub_lbl = tk.Label(
            container, text="Configure os parâmetros de comunicação com o OBS e o dispositivo de vídeo",
            font=FONT_SUBTITLE, bg=COLOR_BG_DARK, fg=COLOR_TEXT_MUTED
        )
        sub_lbl.pack(anchor="w", pady=(0, 16))

        # Estilo genérico de entradas
        lbl_kwargs = {"bg": COLOR_PANEL_BG, "fg": COLOR_TEXT_PRIMARY, "font": FONT_BODY}
        entry_kwargs = {
            "font": FONT_BODY, "bg": COLOR_BG_DARK, "fg": COLOR_TEXT_PRIMARY,
            "insertbackground": COLOR_TEXT_PRIMARY, "relief": tk.FLAT, "highlightthickness": 1,
            "highlightbackground": COLOR_PANEL_BORDER, "highlightcolor": COLOR_ACCENT_CYBER
        }

        # --- Seção 1: OBS WebSocket ---
        obs_frame = tk.LabelFrame(
            container, text=" 🔌 OBS WebSocket 5.x ", bg=COLOR_PANEL_BG,
            fg=COLOR_ACCENT_MINT, font=FONT_SECTION, padx=14, pady=12,
            bd=1, relief=tk.SOLID
        )
        obs_frame.pack(fill=tk.X, pady=(0, 14))

        obs_cfg = self.config_manager.get_obs_config()

        tk.Label(obs_frame, text="Endereço Host:", **lbl_kwargs).grid(row=0, column=0, sticky="w", pady=6)
        self.ent_host = tk.Entry(obs_frame, width=24, **entry_kwargs)
        self.ent_host.insert(0, str(obs_cfg.get("host", "localhost")))
        self.ent_host.grid(row=0, column=1, pady=6, padx=(10, 0))

        tk.Label(obs_frame, text="Porta do Servidor:", **lbl_kwargs).grid(row=1, column=0, sticky="w", pady=6)
        self.ent_port = tk.Entry(obs_frame, width=24, **entry_kwargs)
        self.ent_port.insert(0, str(obs_cfg.get("port", 4455)))
        self.ent_port.grid(row=1, column=1, pady=6, padx=(10, 0))

        tk.Label(obs_frame, text="Senha (Opcional):", **lbl_kwargs).grid(row=2, column=0, sticky="w", pady=6)
        self.ent_pass = tk.Entry(obs_frame, width=24, show="•", **entry_kwargs)
        self.ent_pass.insert(0, str(obs_cfg.get("password", "")))
        self.ent_pass.grid(row=2, column=1, pady=6, padx=(10, 0))

        # --- Seção 2: Gestos & Ações ---
        gesture_frame = tk.LabelFrame(
            container, text=" ✌️ Gesto Peace & 🤟 Número 3 ", bg=COLOR_PANEL_BG,
            fg=COLOR_ACCENT_CYBER, font=FONT_SECTION, padx=14, pady=12,
            bd=1, relief=tk.SOLID
        )
        gesture_frame.pack(fill=tk.X, pady=(0, 14))

        peace_cfg = self.config_manager.get_gesture_config("peace")
        three_cfg = self.config_manager.get_gesture_config("three")

        tk.Label(gesture_frame, text="Cena ✌️ (Peace Sign):", **lbl_kwargs).grid(row=0, column=0, sticky="w", pady=6)
        self.ent_scene = tk.Entry(gesture_frame, width=24, **entry_kwargs)
        self.ent_scene.insert(0, str(peace_cfg.get("scene", "Cena 2")))
        self.ent_scene.grid(row=0, column=1, pady=6, padx=(10, 0))

        tk.Label(gesture_frame, text="Cena 🤟 (Número 3):", **lbl_kwargs).grid(row=1, column=0, sticky="w", pady=6)
        self.ent_three_scene = tk.Entry(gesture_frame, width=24, **entry_kwargs)
        self.ent_three_scene.insert(0, str(three_cfg.get("scene", "Cena 1")))
        self.ent_three_scene.grid(row=1, column=1, pady=6, padx=(10, 0))

        tk.Label(gesture_frame, text="Cooldown (segundos):", **lbl_kwargs).grid(row=2, column=0, sticky="w", pady=6)
        self.ent_cooldown = tk.Entry(gesture_frame, width=24, **entry_kwargs)
        self.ent_cooldown.insert(0, str(peace_cfg.get("cooldown", 1.5)))
        self.ent_cooldown.grid(row=2, column=1, pady=6, padx=(10, 0))

        # --- Seção 3: Câmera ---
        cam_frame = tk.LabelFrame(
            container, text=" 📹 Dispositivo de Vídeo ", bg=COLOR_PANEL_BG,
            fg=COLOR_ACCENT_AMBER, font=FONT_SECTION, padx=14, pady=12,
            bd=1, relief=tk.SOLID
        )
        cam_frame.pack(fill=tk.X, pady=(0, 16))

        cam_cfg = self.config_manager.get_camera_config()

        tk.Label(cam_frame, text="Índice da Webcam (0, 1, 2...):", **lbl_kwargs).grid(row=0, column=0, sticky="w", pady=6)
        self.ent_cam_idx = tk.Entry(cam_frame, width=24, **entry_kwargs)
        self.ent_cam_idx.insert(0, str(cam_cfg.get("device_index", 2)))
        self.ent_cam_idx.grid(row=0, column=1, pady=6, padx=(10, 0))

        # Rodapé / Botões
        btn_box = tk.Frame(container, bg=COLOR_BG_DARK)
        btn_box.pack(fill=tk.X, pady=(8, 0))

        btn_save = tk.Button(
            btn_box, text="💾 SALVAR CONFIGURAÇÕES", font=FONT_BTN,
            bg=COLOR_ACCENT_MINT, fg=COLOR_TEXT_DARK, activebackground="#00d68b",
            relief=tk.FLAT, padx=18, pady=8, cursor="hand2", command=self._save
        )
        btn_save.pack(side=tk.RIGHT, padx=(8, 0))

        btn_cancel = tk.Button(
            btn_box, text="Cancelar", font=FONT_BODY,
            bg=COLOR_PANEL_BG, fg=COLOR_TEXT_MUTED, activebackground=COLOR_PANEL_BORDER,
            relief=tk.FLAT, padx=16, pady=8, cursor="hand2", command=self.destroy
        )
        btn_cancel.pack(side=tk.RIGHT)

    def _save(self):
        try:
            host = self.ent_host.get().strip()
            port = int(self.ent_port.get().strip())
            password = self.ent_pass.get()
            scene = self.ent_scene.get().strip()
            three_scene = self.ent_three_scene.get().strip()
            cooldown = float(self.ent_cooldown.get().strip())
            cam_idx = int(self.ent_cam_idx.get().strip())

            if not host or not scene or not three_scene:
                messagebox.showerror("Erro de Validação", "Host e Nomes de Cena não podem ser vazios!", parent=self)
                return

            saved = self.config_manager.update_settings(
                obs_host=host, obs_port=port, obs_password=password,
                peace_scene=scene, cooldown=cooldown, camera_index=cam_idx,
                three_scene=three_scene
            )

            if saved:
                messagebox.showinfo("Sucesso", "Configurações atualizadas com sucesso!", parent=self)
                if self.on_save_callback:
                    self.on_save_callback()
                self.destroy()
            else:
                messagebox.showerror("Erro", "Falha ao salvar no arquivo config.json.", parent=self)

        except ValueError:
            messagebox.showerror("Erro de Tipo", "Porta, Cooldown e Índice da Câmera devem ser valores numéricos válidos!", parent=self)


class AppGUI:
    """
    Interface Gráfica Principal do OBS Gesture Control.
    Projetada sob os princípios de Revenue-Centric Design (RCD) & Studio-Grade Frontend.
    """
    def __init__(self, root: tk.Tk, config_manager: ConfigManager,
                 obs_controller: OBSController, camera_handler: CameraHandler):
        self.root = root
        self.config_manager = config_manager
        self.obs_controller = obs_controller
        self.camera_handler = camera_handler

        self.root.title("OBS Gesture Control - RCD Studio Deck")
        self.root.geometry("1020x700")
        self.root.minsize(940, 640)
        self.root.configure(bg=COLOR_BG_DARK)

        # Configura callbacks dos handlers
        self.camera_handler.on_frame = self._on_camera_frame
        self.camera_handler.on_gesture_triggered = self._on_gesture_triggered
        self.camera_handler.on_status_change = self._on_camera_status_change

        self.obs_controller.on_status_change = self._on_obs_status_change

        self.current_photo = None
        self._pending_frame = None
        self._pending_gesture_info = None

        self._build_ui()
        self._schedule_gui_updates()

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def _build_ui(self):
        # ---------------------------------------------------------------------
        # 1. BARRA SUPERIOR (HEADER & BRANDING)
        # ---------------------------------------------------------------------
        header = tk.Frame(self.root, bg=COLOR_PANEL_BG, padx=24, pady=12, bd=0)
        header.pack(fill=tk.X)

        brand_box = tk.Frame(header, bg=COLOR_PANEL_BG)
        brand_box.pack(side=tk.LEFT)

        logo_lbl = tk.Label(
            brand_box, text="✌️ OBS GESTURE CONTROL",
            font=FONT_TITLE, bg=COLOR_PANEL_BG, fg=COLOR_ACCENT_MINT
        )
        logo_lbl.pack(side=tk.LEFT)

        tag_lbl = tk.Label(
            brand_box, text="REVENUE-CENTRIC STUDIO",
            font=("Segoe UI", 8, "bold"), bg=COLOR_ACCENT_PURPLE, fg="#ffffff",
            padx=8, pady=2
        )
        tag_lbl.pack(side=tk.LEFT, padx=(12, 0))

        sub_lbl = tk.Label(
            header, text="Automação em Tempo Real por Visão Computacional",
            font=FONT_SUBTITLE, bg=COLOR_PANEL_BG, fg=COLOR_TEXT_MUTED
        )
        sub_lbl.pack(side=tk.RIGHT, pady=(4, 0))

        # Divisor sutil
        divider = tk.Frame(self.root, bg=COLOR_PANEL_BORDER, height=1)
        divider.pack(fill=tk.X)

        # ---------------------------------------------------------------------
        # 2. CARDS DE KPI (F-PATTERN REVENUE-CENTRIC DASHBOARD TOP BAR)
        # ---------------------------------------------------------------------
        kpi_bar = tk.Frame(self.root, bg=COLOR_BG_DARK, padx=20, pady=12)
        kpi_bar.pack(fill=tk.X)

        # Card KPI 1: Status OBS
        self.kpi_obs_card = self._create_kpi_card(
            kpi_bar, title="CONEXÃO OBS WEBSOCKET", value="🔴 DESCONECTADO",
            sub="Porta 4455 (v5.x)", color=COLOR_ACCENT_CORAL
        )
        self.kpi_obs_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8))

        # Card KPI 2: Status Câmera
        self.kpi_cam_card = self._create_kpi_card(
            kpi_bar, title="DISPOSITIVO DE VÍDEO", value="🔴 INATIVA",
            sub=f"Índice {self.camera_handler.device_index}", color=COLOR_ACCENT_CORAL
        )
        self.kpi_cam_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8))

        # Card KPI 3: Gestos Alvo
        peace_cfg = self.config_manager.get_gesture_config("peace")
        three_cfg = self.config_manager.get_gesture_config("three")
        p_scene = peace_cfg.get("scene", "Cena 2")
        t_scene = three_cfg.get("scene", "Cena 1")
        self.kpi_target_card = self._create_kpi_card(
            kpi_bar, title="GESTOS ATIVOS (✌️ / 🤟)", value=f"✌️ {p_scene} | 🤟 {t_scene}",
            sub=f"Cooldown: {peace_cfg.get('cooldown', 1.5)}s", color=COLOR_ACCENT_CYBER
        )
        self.kpi_target_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8))

        # Card KPI 4: Tracking Engine
        self.kpi_engine_card = self._create_kpi_card(
            kpi_bar, title="TRACKING ENGINE", value="🟢 MediaPipe AI",
            sub="HandLandmarker 21 Pts", color=COLOR_ACCENT_MINT
        )
        self.kpi_engine_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # ---------------------------------------------------------------------
        # 3. CONTAINER PRINCIPAL (2 COLUNAS DE DESIGN)
        # ---------------------------------------------------------------------
        main_panel = tk.Frame(self.root, bg=COLOR_BG_DARK)
        main_panel.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))

        # =====================================================================
        # COLUNA ESQUERDA: HERO PREVIEW DA WEBCAM (VALOR PRIMEIRO)
        # =====================================================================
        left_col = tk.Frame(main_panel, bg=COLOR_PANEL_BG, bd=1, relief=tk.SOLID)
        left_col.configure(highlightbackground=COLOR_PANEL_BORDER, highlightthickness=1)
        left_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 16))

        # Cabeçalho do Card da Webcam
        cam_header = tk.Frame(left_col, bg=COLOR_CARD_HEADER, padx=16, pady=10)
        cam_header.pack(fill=tk.X)

        cam_title = tk.Label(
            cam_header, text="📹 PREVIEW DA WEBCAM EM TEMPO REAL",
            font=FONT_SECTION, bg=COLOR_CARD_HEADER, fg=COLOR_TEXT_PRIMARY
        )
        cam_title.pack(side=tk.LEFT)

        self.lbl_mp_indicator = tk.Label(
            cam_header, text="🟢 MediaPipe Landmark Overlay",
            font=("Segoe UI", 8, "bold"), bg=COLOR_CARD_HEADER, fg=COLOR_ACCENT_MINT
        )
        self.lbl_mp_indicator.pack(side=tk.RIGHT)

        # Container do Vídeo (Estabilizado, sem expansão de layout)
        self.video_container = tk.Frame(left_col, bg="#050608")
        self.video_container.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)
        self.video_container.pack_propagate(False)

        # Label onde o frame da câmera é exibido
        self.video_label = tk.Label(
            self.video_container, bg="#050608",
            text="🎥 Câmera Desligada\n\nClique no botão 'Iniciar Câmera' para ativá-la",
            font=("Segoe UI", 12), fg=COLOR_TEXT_MUTED
        )
        self.video_label.pack(fill=tk.BOTH, expand=True)

        # Footer informativo do vídeo
        video_footer = tk.Frame(left_col, bg=COLOR_CARD_HEADER, padx=16, pady=8)
        video_footer.pack(fill=tk.X)

        self.lbl_cam_info = tk.Label(
            video_footer, text="Webcam Status: Inativa | Clique em 'Iniciar Câmera'",
            font=FONT_SUBTITLE, bg=COLOR_CARD_HEADER, fg=COLOR_TEXT_MUTED
        )
        self.lbl_cam_info.pack(side=tk.LEFT)

        # =====================================================================
        # COLUNA DIREITA: PAINEL DE CONTROLE E AÇÕES (ACTIONABLE PANEL)
        # =====================================================================
        right_col = tk.Frame(main_panel, bg=COLOR_BG_DARK, width=340)
        right_col.pack(side=tk.RIGHT, fill=tk.BOTH, expand=False)
        right_col.pack_propagate(False)

        # 1. CARD DE GESTO DETECTADO EM TEMPO REAL
        gesture_card = tk.LabelFrame(
            right_col, text=" GESTO EM TEMPO REAL ", bg=COLOR_PANEL_BG,
            fg=COLOR_ACCENT_AMBER, font=FONT_SECTION, padx=14, pady=14, bd=1, relief=tk.SOLID
        )
        gesture_card.pack(fill=tk.X, pady=(0, 14))

        self.lbl_gesture_display = tk.Label(
            gesture_card, text="— NENHUM —", font=FONT_BADGE,
            bg=COLOR_CARD_HEADER, fg=COLOR_TEXT_MUTED, pady=12, relief=tk.FLAT
        )
        self.lbl_gesture_display.pack(fill=tk.X)

        self.lbl_gesture_progress = tk.Label(
            gesture_card, text="Aguardando sinal da mão...",
            font=FONT_SUBTITLE, bg=COLOR_PANEL_BG, fg=COLOR_TEXT_MUTED
        )
        self.lbl_gesture_progress.pack(anchor="w", pady=(8, 0))

        # 2. CARD DE REGISTRO DE AÇÕES (FEEDBACK & DIREÇÃO)
        action_card = tk.LabelFrame(
            right_col, text=" REGISTRO DE AÇÕES ", bg=COLOR_PANEL_BG,
            fg=COLOR_ACCENT_MINT, font=FONT_SECTION, padx=14, pady=12, bd=1, relief=tk.SOLID
        )
        action_card.pack(fill=tk.X, pady=(0, 14))

        self.lbl_last_action = tk.Label(
            action_card, text="Aguardando primeira validação de gesto...",
            font=FONT_BODY, bg=COLOR_PANEL_BG, fg=COLOR_TEXT_PRIMARY,
            wraplength=290, justify=tk.LEFT, anchor="w"
        )
        self.lbl_last_action.pack(fill=tk.X, pady=4)

        # 3. BOTÕES DE CONTROLE DE ALTO IMPACTO (ACTION CTAS)
        btns_card = tk.Frame(right_col, bg=COLOR_BG_DARK)
        btns_card.pack(fill=tk.X, side=tk.BOTTOM)

        self.btn_toggle_cam = tk.Button(
            btns_card, text="🎥 INICIAR CÂMERA", font=FONT_BTN,
            bg=COLOR_ACCENT_MINT, fg=COLOR_TEXT_DARK, activebackground="#00d68b",
            relief=tk.FLAT, pady=10, cursor="hand2", command=self.toggle_camera
        )
        self.btn_toggle_cam.pack(fill=tk.X, pady=4)

        self.btn_connect_obs = tk.Button(
            btns_card, text="🔌 CONECTAR AO OBS", font=FONT_BTN,
            bg=COLOR_ACCENT_CYBER, fg=COLOR_TEXT_DARK, activebackground="#0096c7",
            relief=tk.FLAT, pady=10, cursor="hand2", command=self.connect_obs
        )
        self.btn_connect_obs.pack(fill=tk.X, pady=4)

        self.btn_test_peace = tk.Button(
            btns_card, text=f"🧪 TESTAR ✌️ ({p_scene})", font=FONT_BTN,
            bg=COLOR_ACCENT_AMBER, fg=COLOR_TEXT_DARK, activebackground="#e0a100",
            relief=tk.FLAT, pady=8, cursor="hand2", command=self.test_peace_gesture
        )
        self.btn_test_peace.pack(fill=tk.X, pady=3)

        self.btn_test_three = tk.Button(
            btns_card, text=f"🧪 TESTAR 🤟 ({t_scene})", font=FONT_BTN,
            bg=COLOR_ACCENT_PURPLE, fg="#ffffff", activebackground="#7b2cbf",
            relief=tk.FLAT, pady=8, cursor="hand2", command=self.test_three_gesture
        )
        self.btn_test_three.pack(fill=tk.X, pady=3)

        self.btn_settings = tk.Button(
            btns_card, text="⚙️ CONFIGURAÇÕES", font=FONT_BTN,
            bg=COLOR_PANEL_BG, fg=COLOR_TEXT_PRIMARY, activebackground=COLOR_PANEL_BORDER,
            relief=tk.FLAT, pady=8, cursor="hand2", command=self.open_settings
        )
        self.btn_settings.pack(fill=tk.X, pady=3)

    def _create_kpi_card(self, parent, title: str, value: str, sub: str, color: str) -> tk.Frame:
        """Helper para construir cards de KPI padronizados (F-Pattern)."""
        card = tk.Frame(parent, bg=COLOR_PANEL_BG, bd=1, relief=tk.SOLID, padx=12, pady=10)
        card.configure(highlightbackground=COLOR_PANEL_BORDER, highlightthickness=1)

        lbl_title = tk.Label(card, text=title, font=FONT_KPI_LBL, bg=COLOR_PANEL_BG, fg=COLOR_TEXT_MUTED)
        lbl_title.pack(anchor="w")

        lbl_val = tk.Label(card, text=value, font=FONT_KPI_VAL, bg=COLOR_PANEL_BG, fg=color)
        lbl_val.pack(anchor="w", pady=(2, 0))

        lbl_sub = tk.Label(card, text=sub, font=FONT_SUBTITLE, bg=COLOR_PANEL_BG, fg=COLOR_TEXT_MUTED)
        lbl_sub.pack(anchor="w")

        # Guarda referência para atualização dinâmica
        card.lbl_val = lbl_val
        card.lbl_sub = lbl_sub
        return card

    def _schedule_gui_updates(self):
        """Agenda atualização periódica suave da GUI a cada ~30ms."""
        if self._pending_frame is not None:
            frame = self._pending_frame
            self._pending_frame = None
            try:
                # Obtém tamanho do container fixo sem disparar expansão
                box_w = self.video_container.winfo_width()
                box_h = self.video_container.winfo_height()
                
                if box_w < 50 or box_h < 50:
                    box_w, box_h = 640, 480

                # Calcula proporção (aspect ratio) para ajustar no container
                h, w, _ = frame.shape
                scale = min(box_w / w, box_h / h)
                new_w = max(1, int(w * scale))
                new_h = max(1, int(h * scale))

                frame_resized = cv2.resize(frame, (new_w, new_h))
                img_rgb = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2RGB)
                img_pil = Image.fromarray(img_rgb)
                self.current_photo = ImageTk.PhotoImage(image=img_pil)
                self.video_label.config(image=self.current_photo, text="")
            except Exception as e:
                pass

        if self._pending_gesture_info is not None:
            detected, candidate, count = self._pending_gesture_info
            self._pending_gesture_info = None

            if detected == "peace" or candidate == "peace":
                self.lbl_gesture_display.config(text="✌️ PEACE", bg=COLOR_ACCENT_MINT, fg=COLOR_TEXT_DARK)
                progress_pct = min(100, int((count / self.camera_handler.required_consecutive_frames) * 100))
                self.lbl_gesture_progress.config(text=f"Detectando ✌️... {progress_pct}%", fg=COLOR_ACCENT_MINT)
            elif detected == "three" or candidate == "three":
                self.lbl_gesture_display.config(text="🤟 NÚMERO 3", bg=COLOR_ACCENT_MINT, fg=COLOR_TEXT_DARK)
                progress_pct = min(100, int((count / self.camera_handler.required_consecutive_frames) * 100))
                self.lbl_gesture_progress.config(text=f"Detectando 🤟 (Nº 3)... {progress_pct}%", fg=COLOR_ACCENT_MINT)
            else:
                self.lbl_gesture_display.config(text="— NENHUM —", bg=COLOR_CARD_HEADER, fg=COLOR_TEXT_MUTED)
                self.lbl_gesture_progress.config(text="Aguardando sinal da mão...", fg=COLOR_TEXT_MUTED)

        self.root.after(30, self._schedule_gui_updates)

    def _on_camera_frame(self, frame, detected_gesture, candidate_gesture, consecutive_count):
        """Callback vindo do thread da câmera."""
        self._pending_frame = frame
        self._pending_gesture_info = (detected_gesture, candidate_gesture, consecutive_count)

    def _on_gesture_triggered(self, gesture_name: str):
        """Disparado quando um gesto é validado de forma consistente."""
        default_scene = "Cena 1" if gesture_name == "three" else "Cena 2"
        gesture_cfg = self.config_manager.get_gesture_config(gesture_name)
        scene_name = gesture_cfg.get("scene", default_scene)
        
        # Executa a troca de cena no OBS
        success, msg = self.obs_controller.change_scene(scene_name)
        timestamp = time.strftime("%H:%M:%S")

        icon = "🤟 (Nº 3)" if gesture_name == "three" else "✌️ (Peace)"
        if success:
            self.lbl_last_action.config(
                text=f"🟢 [{timestamp}] Gesto {icon} Validado:\nCena alterada para '{scene_name}'",
                fg=COLOR_ACCENT_MINT
            )
        else:
            self.lbl_last_action.config(
                text=f"⚠️ [{timestamp}] Gesto {icon} detectado, mas falhou:\n{msg}",
                fg=COLOR_ACCENT_CORAL
            )

    def _on_camera_status_change(self, is_active: bool, message: str):
        """Atualiza a indicação do status da câmera na GUI e nos cards de KPI."""
        def update():
            if is_active:
                self.btn_toggle_cam.config(text="⏹️ PARAR CÂMERA", bg=COLOR_ACCENT_CORAL, fg="#ffffff")
                self.lbl_cam_info.config(text=f"Webcam Status: Ativa (Índice {self.camera_handler.device_index})")
                self.kpi_cam_card.lbl_val.config(text="🟢 ATIVA", fg=COLOR_ACCENT_MINT)
                self.kpi_cam_card.lbl_sub.config(text=f"Dispositivo Índice {self.camera_handler.device_index}")
            else:
                self.btn_toggle_cam.config(text="🎥 INICIAR CÂMERA", bg=COLOR_ACCENT_MINT, fg=COLOR_TEXT_DARK)
                self.video_label.config(image="", text=f"{message}\n\nClique no botão 'Iniciar Câmera' para ativá-la")
                self.lbl_cam_info.config(text="Webcam Status: Inativa")
                self.kpi_cam_card.lbl_val.config(text="🔴 INATIVA", fg=COLOR_ACCENT_CORAL)
                self.kpi_cam_card.lbl_sub.config(text="Desligada")
        self.root.after(0, update)

    def _on_obs_status_change(self, connected: bool, message: str):
        """Atualiza a indicação do status do OBS WebSocket na GUI e nos cards de KPI."""
        def update():
            timestamp = time.strftime("%H:%M:%S")
            if connected:
                self.btn_connect_obs.config(text="🔌 OBS CONECTADO", bg=COLOR_CARD_HEADER, fg=COLOR_ACCENT_MINT)
                self.lbl_last_action.config(text=f"🟢 [{timestamp}] {message}", fg=COLOR_ACCENT_MINT)
                self.kpi_obs_card.lbl_val.config(text="🟢 CONECTADO", fg=COLOR_ACCENT_MINT)
                self.kpi_obs_card.lbl_sub.config(text=f"Porta {self.obs_controller.port}")
            else:
                self.btn_connect_obs.config(text="🔌 CONECTAR AO OBS", bg=COLOR_ACCENT_CYBER, fg=COLOR_TEXT_DARK)
                self.kpi_obs_card.lbl_val.config(text="🔴 DESCONECTADO", fg=COLOR_ACCENT_CORAL)
                self.kpi_obs_card.lbl_sub.config(text="Porta 4455")
                if "falha" in message.lower() or "recusada" in message.lower() or "erro" in message.lower():
                    self.lbl_last_action.config(text=f"🔴 [{timestamp}] {message}", fg=COLOR_ACCENT_CORAL)
        self.root.after(0, update)

    def toggle_camera(self):
        """Liga ou desliga a webcam."""
        if self.camera_handler.is_running:
            self.camera_handler.stop()
        else:
            cam_cfg = self.config_manager.get_camera_config()
            self.camera_handler.device_index = cam_cfg.get("device_index", 2)
            peace_cfg = self.config_manager.get_gesture_config("peace")
            self.camera_handler.set_cooldown(peace_cfg.get("cooldown", 1.5))
            self.camera_handler.start()

    def connect_obs(self):
        """Tenta conectar ao OBS Studio."""
        obs_cfg = self.config_manager.get_obs_config()
        self.obs_controller.update_credentials(
            obs_cfg.get("host", "localhost"),
            int(obs_cfg.get("port", 4455)),
            obs_cfg.get("password", "")
        )
        success, msg = self.obs_controller.connect()
        if not success:
            messagebox.showwarning("Conexão OBS WebSocket", msg, parent=self.root)

    def test_peace_gesture(self):
        """Botão de teste para simular o gesto ✌️ (Peace Sign) manualmente."""
        self._on_gesture_triggered("peace")

    def test_three_gesture(self):
        """Botão de teste para simular o gesto 🤟 (Número 3) manualmente."""
        self._on_gesture_triggered("three")

    def open_settings(self):
        """Abre o diálogo modal de configurações."""
        SettingsDialog(self.root, self.config_manager, self._on_settings_saved)

    def _on_settings_saved(self):
        """Atualiza instâncias em execução após salvar novas configurações."""
        obs_cfg = self.config_manager.get_obs_config()
        self.obs_controller.update_credentials(
            obs_cfg.get("host", "localhost"),
            int(obs_cfg.get("port", 4455)),
            obs_cfg.get("password", "")
        )

        peace_cfg = self.config_manager.get_gesture_config("peace")
        three_cfg = self.config_manager.get_gesture_config("three")
        p_scene = peace_cfg.get("scene", "Cena 2")
        t_scene = three_cfg.get("scene", "Cena 1")
        self.btn_test_peace.config(text=f"🧪 TESTAR ✌️ ({p_scene})")
        self.btn_test_three.config(text=f"🧪 TESTAR 🤟 ({t_scene})")
        self.kpi_target_card.lbl_val.config(text=f"✌️ {p_scene} | 🤟 {t_scene}")
        self.kpi_target_card.lbl_sub.config(text=f"Cooldown: {peace_cfg.get('cooldown', 1.5)}s")
        self.camera_handler.set_cooldown(peace_cfg.get("cooldown", 1.5))

        cam_cfg = self.config_manager.get_camera_config()
        new_cam_idx = cam_cfg.get("device_index", 2)
        if new_cam_idx != self.camera_handler.device_index:
            self.camera_handler.set_device_index(new_cam_idx)

    def on_close(self):
        """Encerra threads e conexões de forma segura antes de fechar a janela."""
        print("[App] Encerrando aplicação...")
        self.camera_handler.stop()
        self.obs_controller.stop_auto_reconnect()
        self.obs_controller.disconnect()
        self.root.destroy()
