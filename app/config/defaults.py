from app.config.models import GestureConfig, ActionConfig, ProfileConfig, AppConfig, OBSConnectionConfig, CameraConfig

def create_default_8_gestures() -> dict[str, GestureConfig]:
    """Cria os 8 gestos pré-definidos padrão do sistema."""
    return {
        "peace": GestureConfig(
            gesture_id="peace",
            icon="✌️",
            default_name="Peace / Paz",
            custom_name="Trocar para Gameplay",
            description="Muda a cena principal para a transmissão de jogos.",
            active=True,
            action=ActionConfig(action_type="switch_scene", scene_name="Gameplay"),
            cooldown=1.5,
            required_frames=8,
            sensitivity=75
        ),
        "thumbs_up": GestureConfig(
            gesture_id="thumbs_up",
            icon="👍",
            default_name="Thumbs Up / Positivo",
            custom_name="Mostrar Câmera",
            description="Ativa a fonte da câmera na cena atual.",
            active=True,
            action=ActionConfig(action_type="enable_source", scene_name="Just Chatting", source_name="Webcam"),
            cooldown=1.5,
            required_frames=8,
            sensitivity=75
        ),
        "thumbs_down": GestureConfig(
            gesture_id="thumbs_down",
            icon="👎",
            default_name="Thumbs Down / Negativo",
            custom_name="Esconder Câmera",
            description="Desativa temporariamente a fonte da webcam.",
            active=True,
            action=ActionConfig(action_type="disable_source", scene_name="Just Chatting", source_name="Webcam"),
            cooldown=1.5,
            required_frames=8,
            sensitivity=75
        ),
        "open_hand": GestureConfig(
            gesture_id="open_hand",
            icon="🖐️",
            default_name="Open Hand / Mão Aberta",
            custom_name="Mutar Microfone",
            description="Muta a fonte de áudio do microfone principal.",
            active=True,
            action=ActionConfig(action_type="mute_source", source_name="Mic/Aux"),
            cooldown=1.5,
            required_frames=8,
            sensitivity=75
        ),
        "fist": GestureConfig(
            gesture_id="fist",
            icon="✊",
            default_name="Fist / Punho Fechado",
            custom_name="Desmutar Microfone",
            description="Ativa o áudio do microfone principal.",
            active=True,
            action=ActionConfig(action_type="unmute_source", source_name="Mic/Aux"),
            cooldown=1.5,
            required_frames=8,
            sensitivity=75
        ),
        "point": GestureConfig(
            gesture_id="point",
            icon="☝️",
            default_name="Point / Apontar",
            custom_name="Trocar para Just Chatting",
            description="Muda a cena ativa para bate-papo com os espectadores.",
            active=True,
            action=ActionConfig(action_type="switch_scene", scene_name="Just Chatting"),
            cooldown=1.5,
            required_frames=8,
            sensitivity=75
        ),
        "love_you": GestureConfig(
            gesture_id="love_you",
            icon="🤟",
            default_name="Love-You / Rock",
            custom_name="Alternar Pausa da Gravação",
            description="Pausa ou retoma a gravação local no OBS.",
            active=True,
            action=ActionConfig(action_type="toggle_record_pause"),
            cooldown=1.5,
            required_frames=8,
            sensitivity=75
        ),
        "pinch": GestureConfig(
            gesture_id="pinch",
            icon="🤏",
            default_name="Pinch / Pinça",
            custom_name="Cena BRB / Intervalo",
            description="Alterna a cena para a tela de 'Volto Já'.",
            active=True,
            action=ActionConfig(action_type="switch_scene", scene_name="BRB"),
            cooldown=1.5,
            required_frames=8,
            sensitivity=75
        )
    }


def create_default_config() -> AppConfig:
    """Gera a estrutura completa de configuração inicial."""
    gestures_gaming = create_default_8_gestures()
    
    gestures_chatting = create_default_8_gestures()
    gestures_chatting["peace"].custom_name = "Cena Chatting Zoom"
    gestures_chatting["point"].custom_name = "Cena Reação"

    gestures_recording = create_default_8_gestures()
    gestures_recording["love_you"].custom_name = "Parar Gravação"
    gestures_recording["love_you"].action = ActionConfig(action_type="stop_record", confirm_required=True)

    profiles = {
        "Live Gaming": ProfileConfig(name="Live Gaming", description="Perfil para transmissões de jogos", gestures=gestures_gaming),
        "Just Chatting": ProfileConfig(name="Just Chatting", description="Perfil para conversar com inscritos", gestures=gestures_chatting),
        "Gravação": ProfileConfig(name="Gravação", description="Perfil otimizado para gravação de tutoriais", gestures=gestures_recording),
        "YouTube": ProfileConfig(name="YouTube", description="Perfil para streams no YouTube", gestures=create_default_8_gestures())
    }

    return AppConfig(
        active_profile="Live Gaming",
        test_mode=False,
        confirm_destructive_actions=True,
        default_cooldown=1.5,
        obs=OBSConnectionConfig(),
        camera=CameraConfig(),
        profiles=profiles
    )
