import os
from datetime import datetime


class MobileVision:
    def __init__(self, vault_path):
        self.vault = vault_path
        if not os.path.exists(self.vault):
            os.makedirs(self.vault)

    def _build_proof_path(self, day_number, task_id, task_name):
        day_folder = os.path.join(self.vault, f"day_{int(day_number):02d}")
        if not os.path.exists(day_folder):
            os.makedirs(day_folder)
        safe_name = "".join(ch for ch in task_name.lower() if ch.isalnum() or ch in ("_", "-"))
        safe_name = safe_name.replace(" ", "_")[:24] or f"task_{task_id}"
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return os.path.join(day_folder, f"task_{task_id}_{safe_name}_{stamp}.jpg")

    def capture_task_proof(self, day_number, task_id, task_name, on_done):
        target = self._build_proof_path(day_number, task_id, task_name)
        try:
            from plyer import camera

            def _finish(result_path):
                if isinstance(result_path, str) and result_path.strip():
                    on_done(result_path)
                else:
                    on_done("")

            camera.take_picture(filename=target, on_complete=_finish)
        except Exception:
            on_done("")

    def capture_progress(self, day_number, on_done):
        target_folder = os.path.join(self.vault, f"day_{int(day_number):02d}")
        if not os.path.exists(target_folder):
            os.makedirs(target_folder)
        target = os.path.join(target_folder, f"progress_day_{int(day_number):02d}.jpg")
        try:
            from plyer import camera

            def _finish(result_path):
                if isinstance(result_path, str) and result_path.strip():
                    on_done(result_path)
                else:
                    on_done("")

            camera.take_picture(filename=target, on_complete=_finish)
        except Exception:
            on_done("")
