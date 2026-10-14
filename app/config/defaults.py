from app.config.models import GestureConfig, ActionConfig, ProfileConfig, AppConfig, OBSConnectionConfig, CameraConfig

def create_default_8_gestures() -> dict[str, GestureConfig]:
    """Cria os 8 gestos pré-definidos padrão do sistema na ordem exata especificada."""
    return {
        "one": GestureConfig(
            gesture_id="one",
            icon="1️⃣",
            default_name="1",
            custom_name="Cena 1",
            description="Muda para a Cena 1 (Dedo indicador levantado).",
            active=True,
            action=ActionConfig(action_type="switch_scene", scene_name="Cena 1"),
            cooldown=1.5,
            required_frames=4,
            sensitivity=60
        ),
        "two": GestureConfig(
            gesture_id="two",
            icon="2️⃣",
            default_name="2",
            custom_name="Cena 2",
            description="Muda para a Cena 2 (Indicador e dedo médio levantados).",
            active=True,
            action=ActionConfig(action_type="switch_scene", scene_name="Cena 2"),
            cooldown=1.5,
            required_frames=4,
            sensitivity=60
        ),
        "three": GestureConfig(
            gesture_id="three",
            icon="3️⃣",
            default_name="3",
            custom_name="Cena 3",
            description="Muda para a Cena 3 (Indicador, dedo médio e anelar levantados).",
            active=True,
            action=ActionConfig(action_type="switch_scene", scene_name="Cena 3"),
            cooldown=1.5,
            required_frames=4,
            sensitivity=60
        ),
        "four": GestureConfig(
            gesture_id="four",
            icon="4️⃣",
            default_name="4",
            custom_name="Cena 4",
            description="Muda para a Cena 4 (Quatro dedos levantados).",
            active=True,
            action=ActionConfig(action_type="switch_scene", scene_name="Cena 4"),
            cooldown=1.5,
            required_frames=4,
            sensitivity=60
        ),
        "five": GestureConfig(
            gesture_id="five",
            icon="🖐️",
            default_name="5",
            custom_name="Mutar Microfone",
            description="Muta o áudio do microfone principal (Todos os 5 dedos abertos).",
            active=True,
            action=ActionConfig(action_type="mute_source", source_name="Mic/Aux"),
            cooldown=1.5,
            required_frames=4,
            sensitivity=60
        ),
        "thumbs_up": GestureConfig(
            gesture_id="thumbs_up",
            icon="👍",
            default_name="JOIA",
            custom_name="Mostrar Câmera",
            description="Ativa a fonte da câmera na cena (Polegar para cima).",
            active=True,
            action=ActionConfig(action_type="enable_source", scene_name="Gameplay", source_name="Webcam"),
            cooldown=1.5,
            required_frames=4,
            sensitivity=60
        ),
        "thumbs_down": GestureConfig(
            gesture_id="thumbs_down",
            icon="👎",
            default_name="JOIA PARA BAIXO",
            custom_name="Esconder Câmera",
            description="Desativa temporariamente a fonte da webcam (Polegar para baixo).",
            active=True,
            action=ActionConfig(action_type="disable_source", scene_name="Gameplay", source_name="Webcam"),
            cooldown=1.5,
            required_frames=4,
            sensitivity=60
        ),
        "fist": GestureConfig(
            gesture_id="fist",
            icon="✊",
            default_name="MÃO FECHADA",
            custom_name="Desmutar Microfone",
            description="Ativa o áudio do microfone (Mão fechada em punho).",
            active=True,
            action=ActionConfig(action_type="unmute_source", source_name="Mic/Aux"),
            cooldown=1.5,
            required_frames=4,
            sensitivity=60
        ),
    }


def create_default_config() -> AppConfig:
    """Gera a estrutura completa de configuração inicial."""
    gestures_gaming = create_default_8_gestures()
    gestures_gaming["one"].custom_name = "Cena Gameplay"
    gestures_gaming["two"].custom_name = "Cena Câmera Cheia"

    gestures_chatting = create_default_8_gestures()
    gestures_chatting["one"].custom_name = "Cena Chatting"
    gestures_chatting["two"].custom_name = "Cena Reação"

    gestures_recording = create_default_8_gestures()
    gestures_recording["fist"].custom_name = "Parar Gravação"
    gestures_recording["fist"].action = ActionConfig(action_type="stop_record", confirm_required=True)

    profiles = {
        "Live Gaming": ProfileConfig(name="Live Gaming", description="Perfil para transmissões de jogos", gestures=gestures_gaming),
        "Just Chatting": ProfileConfig(name="Just Chatting", description="Perfil para conversar com inscritos", gestures=gestures_chatting),
        "Gravação": ProfileConfig(name="Gravação", description="Perfil otimizado para gravação de tutoriais", gestures=gestures_recording),
        "YouTube": ProfileConfig(name="YouTube", description="Perfil para transmissões no YouTube", gestures=create_default_8_gestures())
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
