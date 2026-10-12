import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import List
import time
import threading

ROOT = Path(__file__).resolve().parents[2]
LOGS_DIR = ROOT / "logs"
LOG_FILE = LOGS_DIR / "app.log"

class EventBusHandler(logging.Handler):
    """Handler customizado que envia logs para a GUI através do event bus (H4)."""
    def __init__(self, logger_manager: 'AppLogger'):
        super().__init__()
        self.logger_manager = logger_manager

    def emit(self, record: logging.LogRecord):
        try:
            timestamp = time.strftime("%H:%M:%S", time.localtime(record.created))
            msg = record.getMessage()
            formatted = f"[{timestamp}] [{record.levelname}] {msg}"
            with self.logger_manager._lock:
                self.logger_manager.logs.append(formatted)
                if len(self.logger_manager.logs) > self.logger_manager.max_logs:
                    self.logger_manager.logs.pop(0)

            from app.core.events import event_bus
            event_bus.publish(
                "on_log_message",
                log_text=formatted,
                level=record.levelname,
                timestamp=timestamp,
                message=msg
            )
        except Exception:
            self.handleError(record)


class AppLogger:
    """
    Gerenciador centralizado de logs baseado no módulo logging padrão do Python.
    Suporta console, arquivo rotativo (logs/app.log) e eventos da interface gráfica.
    """
    _instance = None
    _lock = threading.RLock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(AppLogger, cls).__new__(cls)
                cls._instance.logs: List[str] = []
                cls._instance.max_logs = 500
                cls._instance._setup_logger()
            return cls._instance

    def _setup_logger(self):
        self._logger = logging.getLogger("OBSGestureControl")
        self._logger.setLevel(logging.DEBUG)
        self._logger.propagate = False

        if not self._logger.handlers:
            # 1. Handler para Console
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(logging.INFO)
            console_formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
            console_handler.setFormatter(console_formatter)
            self._logger.addHandler(console_handler)

            # 2. Handler para Arquivo Rotativo (logs/app.log)
            try:
                LOGS_DIR.mkdir(parents=True, exist_ok=True)
                file_handler = RotatingFileHandler(
                    str(LOG_FILE),
                    maxBytes=2 * 1024 * 1024,
                    backupCount=3,
                    encoding="utf-8"
                )
                file_handler.setLevel(logging.DEBUG)
                file_formatter = logging.Formatter(
                    "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S"
                )
                file_handler.setFormatter(file_formatter)
                self._logger.addHandler(file_handler)
            except Exception as e:
                print(f"[Logger] Não foi possível criar arquivo de log em {LOG_FILE}: {e}")

            # 3. Handler para Event Bus (GUI)
            eb_handler = EventBusHandler(self)
            eb_handler.setLevel(logging.INFO)
            self._logger.addHandler(eb_handler)

    def log(self, message: str, level: str = "INFO"):
        lvl = getattr(logging, level.upper(), logging.INFO)
        self._logger.log(lvl, message)

    def debug(self, message: str):
        self._logger.debug(message)

    def info(self, message: str):
        self._logger.info(message)

    def warning(self, message: str):
        self._logger.warning(message)

    def error(self, message: str):
        self._logger.error(message)

    def get_logs(self) -> List[str]:
        with self._lock:
            return list(self.logs)

    def clear(self):
        with self._lock:
            self.logs.clear()
        from app.core.events import event_bus
        event_bus.publish(
            "on_log_message",
            log_text="[System] Logs limpos.",
            level="INFO",
            timestamp=time.strftime("%H:%M:%S"),
            message="Logs limpos"
        )

logger = AppLogger()
