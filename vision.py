import cv2
import os
import ctypes
import shutil
from datetime import datetime

class GlowVision:
    def __init__(self, vault_path="glowup_vault"):
        self.vault = vault_path
        if not os.path.exists(self.vault):
            os.makedirs(self.vault)
            self._hide_vault_on_windows()

    def _hide_vault_on_windows(self):
        if os.name != "nt":
            return
        FILE_ATTRIBUTE_HIDDEN = 0x02
        try:
            ctypes.windll.kernel32.SetFileAttributesW(self.vault, FILE_ATTRIBUTE_HIDDEN)
        except Exception:
            pass

    def _capture_image(self, window_title, save_path, overlay_path=None):
        cap = cv2.VideoCapture(0)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

        overlay = cv2.imread(overlay_path) if overlay_path and os.path.exists(overlay_path) else None
        captured = False

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            display = frame.copy()
            if overlay is not None:
                overlay_res = cv2.resize(overlay, (frame.shape[1], frame.shape[0]))
                cv2.addWeighted(overlay_res, 0.3, display, 0.7, 0, display)

            cv2.putText(
                display,
                "SPACE = Capture | ESC = Cancel",
                (20, 36),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (255, 255, 255),
                2,
                cv2.LINE_AA,
            )

            cv2.imshow(window_title, display)
            key = cv2.waitKey(1)
            if key == 32:  # Space
                cv2.imwrite(save_path, frame)
                captured = True
                break
            if key == 27:  # Esc
                break

        cap.release()
        cv2.destroyAllWindows()
        return captured

    def capture_task_proof(self, day_number, task_id, task_name, with_overlay=False):
        day_folder = os.path.join(self.vault, f"day_{int(day_number):02d}")
        if not os.path.exists(day_folder):
            os.makedirs(day_folder)

        safe_name = "".join(ch for ch in task_name.lower() if ch.isalnum() or ch in ("_", "-"))
        safe_name = safe_name.replace(" ", "_")[:24] or f"task_{task_id}"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_path = os.path.join(day_folder, f"task_{task_id}_{safe_name}_{timestamp}.jpg")

        overlay_path = None
        if with_overlay:
            overlay_path = os.path.join(self.vault, "progress_day_1.jpg")

        title = f"Proof Capture - {task_name}"
        captured = self._capture_image(title, save_path=save_path, overlay_path=overlay_path)
        if captured:
            if with_overlay:
                progress_path = os.path.join(self.vault, f"progress_day_{int(day_number)}.jpg")
                try:
                    shutil.copyfile(save_path, progress_path)
                except OSError:
                    pass
            return save_path
        return ""

    def capture_progress(self, day_number):
        day_number = int(day_number)
        current_path = os.path.join(self.vault, f"progress_day_{day_number}.jpg")
        overlay_path = os.path.join(self.vault, "progress_day_1.jpg") if day_number > 1 else None

        captured = self._capture_image(
            "GlowUp Cam: SPACE to Snap | ESC to Exit",
            save_path=current_path,
            overlay_path=overlay_path,
        )
        return captured
