from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional

@dataclass
class ActionConfig:
    action_type: str = "switch_scene"  # Ex: switch_scene, enable_source, disable_source, toggle_source, start_stream, etc.
    scene_name: str = ""
    source_name: str = ""
    volume_db: float = 0.0
    command_str: str = ""
    confirm_required: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ActionConfig':
        if not isinstance(data, dict):
            return cls()
        return cls(
            action_type=data.get("action_type", "switch_scene"),
            scene_name=data.get("scene_name", ""),
            source_name=data.get("source_name", ""),
            volume_db=float(data.get("volume_db", 0.0)),
            command_str=data.get("command_str", ""),
            confirm_required=bool(data.get("confirm_required", False))
        )


KNOWN_GESTURE_IDS = {
    "peace",
    "thumbs_up",
    "thumbs_down",
    "open_hand",
    "fist",
    "point",
    "love_you",
    "pinch"
}

@dataclass
class GestureConfig:
    gesture_id: str
    icon: str
    default_name: str
    custom_name: str
    description: str
    active: bool = True
    action: ActionConfig = field(default_factory=ActionConfig)
    cooldown: float = 1.5
    required_frames: int = 8
    sensitivity: int = 75  # 0 a 100%

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["action"] = self.action.to_dict()
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GestureConfig':
        action_data = data.get("action", {})
        action_obj = ActionConfig.from_dict(action_data)
        cooldown_val = max(0.0, float(data.get("cooldown", 1.5)))
        req_frames_val = max(1, min(60, int(data.get("required_frames", 8))))
        sens_val = max(0, min(100, int(data.get("sensitivity", 75))))
        return cls(
            gesture_id=data.get("gesture_id", "peace"),
            icon=data.get("icon", "✌️"),
            default_name=data.get("default_name", "Peace"),
            custom_name=data.get("custom_name", data.get("default_name", "Peace")),
            description=data.get("description", ""),
            active=bool(data.get("active", True)),
            action=action_obj,
            cooldown=cooldown_val,
            required_frames=req_frames_val,
            sensitivity=sens_val
        )


@dataclass
class ProfileConfig:
    name: str
    description: str = ""
    gestures: Dict[str, GestureConfig] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "gestures": {k: v.to_dict() for k, v in self.gestures.items()}
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProfileConfig':
        name = data.get("name", "Default")
        desc = data.get("description", "")
        raw_gestures = data.get("gestures", {})
        gestures_dict = {}
        for k, v in raw_gestures.items():
            g_id = v.get("gesture_id", k) if isinstance(v, dict) else k
            if g_id in KNOWN_GESTURE_IDS:
                gestures_dict[g_id] = GestureConfig.from_dict(v)
        return cls(name=name, description=desc, gestures=gestures_dict)


@dataclass
class OBSConnectionConfig:
    host: str = "localhost"
    port: int = 4455
    password: str = "123456"
    auto_connect: bool = True
    auto_reconnect: bool = True
    reconnect_interval: float = 5.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'OBSConnectionConfig':
        if not isinstance(data, dict):
            return cls()
        port_val = max(1, min(65535, int(data.get("port", 4455))))
        return cls(
            host=data.get("host", "localhost"),
            port=port_val,
            password=str(data.get("password", "123456")),
            auto_connect=bool(data.get("auto_connect", True)),
            auto_reconnect=bool(data.get("auto_reconnect", True)),
            reconnect_interval=float(data.get("reconnect_interval", 5.0))
        )


@dataclass
class CameraConfig:
    device_index: int = 0
    target_fps: int = 30
    resolution_width: int = 1280
    resolution_height: int = 720
    draw_landmarks: bool = True
    draw_overlay: bool = True
    max_hands: int = 2
    min_detection_confidence: float = 0.5
    min_presence_confidence: float = 0.5
    min_tracking_confidence: float = 0.5
    preferred_hand: str = "any"  # "any", "left", "right"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CameraConfig':
        if not isinstance(data, dict):
            return cls()
        target_fps_val = max(5, min(60, int(data.get("target_fps", 30))))
        return cls(
            device_index=int(data.get("device_index", 0)),
            target_fps=target_fps_val,
            resolution_width=int(data.get("resolution_width", 1280)),
            resolution_height=int(data.get("resolution_height", 720)),
            draw_landmarks=bool(data.get("draw_landmarks", True)),
            draw_overlay=bool(data.get("draw_overlay", True)),
            max_hands=int(data.get("max_hands", 2)),
            min_detection_confidence=float(data.get("min_detection_confidence", 0.5)),
            min_presence_confidence=float(data.get("min_presence_confidence", 0.5)),
            min_tracking_confidence=float(data.get("min_tracking_confidence", 0.5)),
            preferred_hand=str(data.get("preferred_hand", "any"))
        )


@dataclass
class AppConfig:
    active_profile: str = "Live Gaming"
    test_mode: bool = False
    confirm_destructive_actions: bool = True
    default_cooldown: float = 1.5
    obs: OBSConnectionConfig = field(default_factory=OBSConnectionConfig)
    camera: CameraConfig = field(default_factory=CameraConfig)
    profiles: Dict[str, ProfileConfig] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "active_profile": self.active_profile,
            "test_mode": self.test_mode,
            "confirm_destructive_actions": self.confirm_destructive_actions,
            "default_cooldown": self.default_cooldown,
            "obs": self.obs.to_dict(),
            "camera": self.camera.to_dict(),
            "profiles": {k: v.to_dict() for k, v in self.profiles.items()}
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AppConfig':
        active_prof = data.get("active_profile", "Live Gaming")
        test_mode = bool(data.get("test_mode", False))
        confirm_dest = bool(data.get("confirm_destructive_actions", True))
        def_cooldown = float(data.get("default_cooldown", 1.5))
        
        obs_cfg = OBSConnectionConfig.from_dict(data.get("obs", {}))
        cam_cfg = CameraConfig.from_dict(data.get("camera", {}))

        raw_profiles = data.get("profiles", {})
        profiles_dict = {}
        for p_name, p_val in raw_profiles.items():
            profiles_dict[p_name] = ProfileConfig.from_dict(p_val)

        return cls(
            active_profile=active_prof,
            test_mode=test_mode,
            confirm_destructive_actions=confirm_dest,
            default_cooldown=def_cooldown,
            obs=obs_cfg,
            camera=cam_cfg,
            profiles=profiles_dict
        )
