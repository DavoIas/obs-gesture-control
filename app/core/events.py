import time
import threading
from typing import Callable, Dict, List, Any

class EventBus:
    """
    Barramento de eventos thread-safe para comunicação desacoplada entre
    visão computacional, controlador OBS, gerenciador de estado e interface GUI.
    """
    _instance = None
    _lock = threading.RLock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(EventBus, cls).__new__(cls)
                cls._instance._subscribers = {}
            return cls._instance

    def subscribe(self, event_type: str, callback: Callable[..., None]):
        with self._lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            if callback not in self._subscribers[event_type]:
                self._subscribers[event_type].append(callback)

    def unsubscribe(self, event_type: str, callback: Callable[..., None]):
        with self._lock:
            if event_type in self._subscribers and callback in self._subscribers[event_type]:
                self._subscribers[event_type].remove(callback)

    def publish(self, event_type: str, **kwargs):
        with self._lock:
            callbacks = list(self._subscribers.get(event_type, []))
        
        for callback in callbacks:
            try:
                callback(**kwargs)
            except Exception as e:
                try:
                    from app.core.logger import logger
                    logger.error(f"[EventBus] Erro ao disparar callback em '{event_type}': {e}")
                except Exception:
                    pass

# Instância global para importação facilitada
event_bus = EventBus()
