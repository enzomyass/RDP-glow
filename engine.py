import copy
import json
import os
from datetime import date, datetime


DEFAULT_SETTINGS = {
    "sleep_lock_start": "21:00",
    "sleep_lock_end": "05:00",
    "reminders_enabled": True,
    "sound_enabled": True,
    "strict_guard": True,
    "weather_city": "Manila",
}

EXERCISE_LIBRARY = [
    ("Plank Hold", "seconds", 35),
    ("Dead Bug", "reps", 16),
    ("Mountain Climbers", "reps", 24),
    ("Bicycle Crunches", "reps", 20),
    ("Reverse Crunch", "reps", 14),
    ("Leg Raises", "reps", 12),
    ("Jumping Jacks", "reps", 35),
    ("Bodyweight Squats", "reps", 18),
    ("High Knees", "seconds", 30),
    ("Russian Twists", "reps", 20),
]


class GlowEngine:
    def __init__(self, data_path="data.json"):
        self.data_path = data_path
        self.data = self.load_data()
        self._advance_day_if_needed()
        self.refresh_daily_plan()
        self.save_data()

    def _default_data(self):
        today = date.today().isoformat()
        return {
            "day": 1,
            "start_date": today,
            "last_reset_date": today,
            "tasks": self._build_tasks(day=1, existing_by_id=None),
            "settings": copy.deepcopy(DEFAULT_SETTINGS),
            "weather": {
                "status": "not_checked",
                "good_for_walk": True,
                "summary": "Weather not checked yet.",
                "checked_at": "",
            },
        }

    def _is_valid_time(self, value):
        if not isinstance(value, str):
            return False
        try:
            datetime.strptime(value, "%H:%M")
            return True
        except ValueError:
            return False

    def _normalize_settings(self, raw_settings):
        settings = copy.deepcopy(DEFAULT_SETTINGS)
        if not isinstance(raw_settings, dict):
            return settings

        for key, default_value in DEFAULT_SETTINGS.items():
            if key not in raw_settings:
                continue

            if isinstance(default_value, bool):
                settings[key] = bool(raw_settings.get(key))
            elif key in {"sleep_lock_start", "sleep_lock_end"}:
                candidate = raw_settings.get(key)
                if self._is_valid_time(candidate):
                    settings[key] = candidate
            elif isinstance(default_value, str):
                candidate = raw_settings.get(key)
                if isinstance(candidate, str) and candidate.strip():
                    settings[key] = candidate.strip()
        return settings

    def _build_daily_exercises(self, day):
        day_index = max(1, int(day)) - 1
        workout_count = 3 if day % 2 else 2
        difficulty_block = day_index // 5
        increment = difficulty_block * 3
        start = day_index % len(EXERCISE_LIBRARY)

        picks = []
        for offset in range(workout_count):
            name, unit, base = EXERCISE_LIBRARY[(start + offset) % len(EXERCISE_LIBRARY)]
            target = base + increment
            if unit == "seconds":
                picks.append(f"{name}: {target}s")
            else:
                picks.append(f"{name}: {target} reps")
        return picks

    def get_daily_exercises(self, day=None):
        if day is None:
            day = self.data.get("day", 1)
        return self._build_daily_exercises(day)

    def _task_blueprints(self, day):
        exercises = self._build_daily_exercises(day)
        return [
            {
                "id": 1,
                "name": "Morning Water",
                "target_time": "04:55",
                "note": "Drink at least 400-500ml before jog.",
                "requires_proof": True,
            },
            {
                "id": 2,
                "name": "30-Min Morning Jog/Walk",
                "target_time": "05:00",
                "note": "Outdoor cardio goal. Weather scan can move this indoors.",
                "requires_proof": True,
            },
            {
                "id": 3,
                "name": "GlutaGenC (Pre-Breakfast)",
                "target_time": "06:00",
                "note": "Take before breakfast, then wait 30-60 minutes.",
                "requires_proof": True,
            },
            {
                "id": 4,
                "name": "Small Breakfast",
                "target_time": "06:45",
                "note": "Low-rice breakfast. Keep it controlled and light.",
                "requires_proof": True,
            },
            {
                "id": 5,
                "name": "Probiotic Supplement",
                "target_time": "07:05",
                "note": "Take shortly after breakfast.",
                "requires_proof": True,
            },
            {
                "id": 6,
                "name": "Afternoon Abs/Fat-Loss Workout",
                "target_time": "16:15",
                "note": " | ".join(exercises),
                "requires_proof": True,
            },
            {
                "id": 7,
                "name": "GlutaGenC (Bedtime)",
                "target_time": "20:30",
                "note": "Take before final wind-down.",
                "requires_proof": True,
            },
            {
                "id": 8,
                "name": "Skin Care Routine",
                "target_time": "20:40",
                "note": "Night routine before sleep lock starts.",
                "requires_proof": True,
            },
            {
                "id": 9,
                "name": "Sleep Reminder / Lockout",
                "target_time": "21:00",
                "note": "Sleep window enforced until 05:00.",
                "requires_proof": True,
            },
        ]

    def _build_tasks(self, day, existing_by_id):
        templates = self._task_blueprints(day)
        existing_by_id = existing_by_id or {}
        tasks = []

        for template in templates:
            old = existing_by_id.get(template["id"], {})
            proof_path = old.get("proof_path")
            if not isinstance(proof_path, str):
                proof_path = ""

            done = bool(old.get("done", False))
            if template["requires_proof"] and not proof_path:
                done = False

            task = {
                "id": template["id"],
                "name": template["name"],
                "done": done,
                "requires_proof": bool(template["requires_proof"]),
                "target_time": template["target_time"],
                "note": template["note"],
                "proof_path": proof_path,
                "completed_at": old.get("completed_at", ""),
            }
            tasks.append(task)
        return tasks

    def _normalize_tasks(self, raw_tasks, day):
        raw_tasks = raw_tasks if isinstance(raw_tasks, list) else []
        existing_by_id = {}

        for item in raw_tasks:
            if not isinstance(item, dict):
                continue
            task_id = item.get("id")
            if isinstance(task_id, int):
                existing_by_id[task_id] = item

        return self._build_tasks(day=day, existing_by_id=existing_by_id)

    def load_data(self):
        defaults = self._default_data()
        if not os.path.exists(self.data_path):
            return defaults

        try:
            with open(self.data_path, "r", encoding="utf-8") as file:
                loaded = json.load(file)
        except (OSError, json.JSONDecodeError):
            return defaults

        if not isinstance(loaded, dict):
            return defaults

        day = loaded.get("day", defaults["day"])
        try:
            day = int(day)
        except (TypeError, ValueError):
            day = defaults["day"]
        day = max(1, min(30, day))

        start_date = loaded.get("start_date", defaults["start_date"])
        if not isinstance(start_date, str) or not start_date.strip():
            start_date = defaults["start_date"]

        last_reset_date = loaded.get("last_reset_date", defaults["last_reset_date"])
        if not isinstance(last_reset_date, str) or not last_reset_date.strip():
            last_reset_date = defaults["last_reset_date"]

        weather = loaded.get("weather")
        if not isinstance(weather, dict):
            weather = defaults["weather"]
        else:
            weather = {
                "status": str(weather.get("status", "not_checked")),
                "good_for_walk": bool(weather.get("good_for_walk", True)),
                "summary": str(weather.get("summary", "Weather not checked yet.")),
                "checked_at": str(weather.get("checked_at", "")),
            }

        return {
            "day": day,
            "start_date": start_date,
            "last_reset_date": last_reset_date,
            "tasks": self._normalize_tasks(loaded.get("tasks"), day=day),
            "settings": self._normalize_settings(loaded.get("settings")),
            "weather": weather,
        }

    def _advance_day_if_needed(self):
        today = date.today()
        last_reset_raw = self.data.get("last_reset_date", today.isoformat())
        try:
            last_reset = date.fromisoformat(last_reset_raw)
        except ValueError:
            last_reset = today

        if today <= last_reset:
            self.data["last_reset_date"] = today.isoformat()
            return

        delta_days = (today - last_reset).days
        current_day = int(self.data.get("day", 1))
        next_day = min(30, current_day + max(0, delta_days))
        self.data["day"] = next_day
        self.data["last_reset_date"] = today.isoformat()

        # New day means a clean discipline slate.
        self.data["tasks"] = self._build_tasks(day=next_day, existing_by_id=None)

    def refresh_daily_plan(self):
        day = int(self.data.get("day", 1))
        current_tasks = self.data.get("tasks", [])
        existing_by_id = {
            task.get("id"): task for task in current_tasks if isinstance(task, dict) and isinstance(task.get("id"), int)
        }
        self.data["tasks"] = self._build_tasks(day=day, existing_by_id=existing_by_id)
        self.save_data()

    def save_data(self):
        with open(self.data_path, "w", encoding="utf-8") as file:
            json.dump(self.data, file, indent=4)

    def get_progress(self):
        tasks = self.data.get("tasks", [])
        if not tasks:
            return 0
        done = sum(1 for task in tasks if task.get("done"))
        return int((done / len(tasks)) * 100)

    def count_completed(self):
        return sum(1 for task in self.data.get("tasks", []) if task.get("done"))

    def get_task(self, task_id):
        for task in self.data.get("tasks", []):
            if task.get("id") == task_id:
                return task
        return None

    def get_tasks(self):
        return list(self.data.get("tasks", []))

    def get_proof_tasks(self):
        return [task for task in self.data.get("tasks", []) if task.get("proof_path")]

    def is_morning_ready(self):
        morning_ids = {1, 2}
        morning = [task for task in self.data.get("tasks", []) if task.get("id") in morning_ids]
        if not morning:
            return False
        return all(task.get("done") for task in morning)

    def mark_task_with_proof(self, task_id, proof_path):
        task = self.get_task(task_id)
        if not task:
            return False

        task["proof_path"] = proof_path
        task["done"] = True
        task["completed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.save_data()
        return True

    def reset_task(self, task_id):
        task = self.get_task(task_id)
        if not task:
            return False
        task["done"] = False
        task["proof_path"] = ""
        task["completed_at"] = ""
        self.save_data()
        return True

    def update_setting(self, key, value):
        if key not in DEFAULT_SETTINGS:
            return
        if key in {"sleep_lock_start", "sleep_lock_end"} and not self._is_valid_time(value):
            return
        self.data["settings"][key] = value
        self.save_data()

    def apply_weather_result(self, good_for_walk, summary):
        weather = {
            "status": "ok",
            "good_for_walk": bool(good_for_walk),
            "summary": summary,
            "checked_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }
        self.data["weather"] = weather

        walk = self.get_task(2)
        if walk:
            if good_for_walk:
                walk["name"] = "30-Min Morning Jog/Walk"
                walk["target_time"] = "05:00"
                walk["note"] = f"Outdoor cardio approved. {summary}"
            else:
                walk["name"] = "30-Min Indoor Walk / March"
                walk["target_time"] = "05:30"
                walk["note"] = f"Weather fallback enabled. {summary}"
        self.save_data()

    def is_sleep_window_active(self, now=None):
        now = now or datetime.now()
        now_text = now.strftime("%H:%M")

        settings = self.data.get("settings", {})
        start = settings.get("sleep_lock_start", "21:00")
        end = settings.get("sleep_lock_end", "05:00")

        if not self._is_valid_time(start) or not self._is_valid_time(end):
            return False

        if start < end:
            return start <= now_text < end
        return now_text >= start or now_text < end

    def reset_all_tasks_for_today(self):
        existing = {task["id"]: {"done": False, "proof_path": "", "completed_at": ""} for task in self.get_tasks()}
        self.data["tasks"] = self._build_tasks(day=self.data.get("day", 1), existing_by_id=existing)
        self.save_data()
