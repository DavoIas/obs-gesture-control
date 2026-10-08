import sys
import os
import signal

# Adicionar pasta raiz ao PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.gui.main_window import MainWindow
from app.vision.camera import camera_handler
from app.obs.controller import obs_controller
from app.core.logger import logger

def main():
    logger.log("=========================================")
    logger.log("  Iniciando OBS Gesture Control V2.0")
    logger.log("=========================================")

    app = MainWindow()

    def on_closing():
        logger.log("Encerrando aplicação OBS Gesture Control...")
        try:
            camera_handler.stop()
            obs_controller.disconnect()
        except Exception:
            pass
        app.destroy()

    app.protocol("WM_DELETE_WINDOW", on_closing)

    try:
        app.mainloop()
    except KeyboardInterrupt:
        on_closing()

if __name__ == "__main__":
    main()
