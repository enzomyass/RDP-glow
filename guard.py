import psutil

class GlowGuard:
    def __init__(self, engine):
        self.engine = engine
        self.distractions = {
            "chrome.exe",
            "msedge.exe",
            "firefox.exe",
            "opera.exe",
            "discord.exe",
            "steam.exe",
            "epicgameslauncher.exe",
            "riotclientservices.exe",
            "valorant.exe",
            "dota2.exe",
            "leagueclient.exe",
        }

    def set_distractions(self, process_names):
        cleaned = {
            str(name).strip().lower()
            for name in process_names
            if isinstance(name, str) and name.strip()
        }
        if cleaned:
            self.distractions = cleaned

    def enforce_lockout(self, force=False):
        if not force and self.engine.is_morning_ready():
            return

        for proc in psutil.process_iter(["name"]):
            name = (proc.info.get("name") or "").lower()
            if name in self.distractions:
                try:
                    proc.kill()
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
