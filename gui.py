import json
import os
import threading
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta

import customtkinter as ctk

from engine import GlowEngine
from guard import GlowGuard
from vision import GlowVision

try:
    import winsound
except ImportError:
    winsound = None


class GlowApp(ctk.CTk):
    TABS = ("Home", "Routine", "Guard", "Vault", "Settings")
    CARD_COLORS = ("#FFD36B", "#BFD7FF", "#FFBEE8", "#BEF2D5", "#FFD9A8", "#BBD9FF", "#E3CEFF", "#AEEED5", "#D8D3FF")

    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")

        self.engine = GlowEngine()
        self.vision = GlowVision()
        self.guard = GlowGuard(self.engine)

        self.active_tab = "Home"
        self.weather_loading = False
        self.reminder_keys = set()
        self.sleep_lock_window = None
        self.sleep_lock_label = None
        self.inputs = {}

        self.title("30-Day Glow Up Console")
        self.geometry("600x980")
        self.minsize(560, 900)
        self.configure(fg_color="#CFC2EB")

        self._build_shell()
        self._show_splash()

    def _build_shell(self):
        self.phone_shell = ctk.CTkFrame(self, fg_color="#1B1F36", corner_radius=48, border_width=2, border_color="#353B58", width=448, height=900)
        self.phone_shell.pack(pady=24)
        self.phone_shell.pack_propagate(False)

        self.screen = ctk.CTkFrame(self.phone_shell, fg_color="#F7F7FB", corner_radius=38)
        self.screen.pack(fill="both", expand=True, padx=12, pady=12)

        self.content = ctk.CTkFrame(self.screen, fg_color="transparent")
        self.content.pack(fill="both", expand=True, padx=14, pady=(14, 8))

        self.navbar = ctk.CTkFrame(self.screen, fg_color="#101223", corner_radius=24, height=58)
        self.navbar.pack(fill="x", padx=14, pady=(0, 14))
        self.navbar.pack_propagate(False)

    def _show_splash(self):
        self.splash = ctk.CTkFrame(self.screen, fg_color="#101223", corner_radius=30)
        self.splash.place(relx=0, rely=0, relwidth=1, relheight=1)
        ctk.CTkLabel(self.splash, text="RDP Glow", font=("Bahnschrift SemiBold", 50), text_color="#F4F4FF").place(relx=0.5, rely=0.44, anchor="center")
        ctk.CTkLabel(self.splash, text="Discipline Console", font=("Segoe UI", 16), text_color="#A5A9C8").place(relx=0.5, rely=0.5, anchor="center")
        self.splash_bar = ctk.CTkProgressBar(self.splash, width=240, height=10, corner_radius=999, fg_color="#2A2E48", progress_color="#BCA9FF")
        self.splash_bar.place(relx=0.5, rely=0.57, anchor="center")
        self.splash_bar.set(0)
        self._animate_splash(0)

    def _animate_splash(self, step):
        value = min(1.0, step / 30)
        self.splash_bar.set(value)
        if value >= 1.0:
            self.after(150, self._finish_boot)
            return
        self.after(36, lambda: self._animate_splash(step + 1))

    def _finish_boot(self):
        self.splash.destroy()
        self.render_tab(animate=True)
        self._lock_tick()
        self._reminder_tick()
        self._weather_tick()
        self.refresh_weather_async()

    def _clear(self, frame):
        for child in frame.winfo_children():
            child.destroy()

    def switch_tab(self, tab):
        self.active_tab = tab
        self.render_tab(animate=False)

    def render_tab(self, animate=False):
        self._clear(self.content)
        self._clear(self.navbar)
        if self.active_tab == "Home":
            self._render_home(animate=animate)
        elif self.active_tab == "Routine":
            self._render_routine()
        elif self.active_tab == "Guard":
            self._render_guard()
        elif self.active_tab == "Vault":
            self._render_vault()
        else:
            self._render_settings()
        self._render_navbar()

    def _render_header(self, tab_name):
        row = ctk.CTkFrame(self.content, fg_color="transparent")
        row.pack(fill="x", pady=(2, 10))
        avatar = ctk.CTkFrame(row, width=46, height=46, corner_radius=23, fg_color="#11142A")
        avatar.pack(side="left")
        avatar.pack_propagate(False)
        ctk.CTkLabel(avatar, text="R", font=("Bahnschrift Bold", 18), text_color="#F7F7FB").pack(expand=True)
        info = ctk.CTkFrame(row, fg_color="transparent")
        info.pack(side="left", padx=12)
        ctk.CTkLabel(info, text="Hello, Champion", font=("Bahnschrift SemiBold", 21), text_color="#1B1E33").pack(anchor="w")
        day = self.engine.data.get("day", 1)
        ctk.CTkLabel(info, text=f"Day {day} | {datetime.now().strftime('%a, %d %b %Y')} | {tab_name}", font=("Segoe UI", 12), text_color="#6A6B7D").pack(anchor="w")

    def _render_home(self, animate=False):
        tasks = self.engine.get_tasks()
        progress = self.engine.get_progress()
        completed = self.engine.count_completed()
        weather_text = self.engine.data.get("weather", {}).get("summary", "Weather not checked yet.")
        self._render_header("Home")

        hero = ctk.CTkFrame(self.content, fg_color="#8D7AFC", corner_radius=24)
        hero.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(hero, text="Daily challenge", font=("Bahnschrift SemiBold", 36), text_color="#10112B").pack(anchor="w", padx=18, pady=(14, 0))
        gate = "Guard active until Morning Water + Jog are proved." if not self.engine.is_morning_ready() else "Morning gate unlocked. Keep moving."
        ctk.CTkLabel(hero, text=gate, font=("Segoe UI", 12), text_color="#1F2040").pack(anchor="w", padx=18, pady=(4, 0))
        ctk.CTkLabel(hero, text=f"Weather: {weather_text}", font=("Segoe UI", 11), text_color="#2B2D52", wraplength=355, justify="left").pack(anchor="w", padx=18, pady=(2, 8))
        self.hero_bar = ctk.CTkProgressBar(hero, height=10, fg_color="#CDC3FF", progress_color="#11152C")
        self.hero_bar.pack(fill="x", padx=18)
        self.hero_bar.set(0 if animate else progress / 100)
        ctk.CTkLabel(hero, text=f"{progress}% complete | {completed}/{len(tasks)} proofs submitted", font=("Segoe UI Semibold", 12), text_color="#1E2243").pack(anchor="w", padx=18, pady=(8, 14))

        strip = ctk.CTkFrame(self.content, fg_color="transparent")
        strip.pack(fill="x", pady=(0, 10))
        current_day = self.engine.data.get("day", 1)
        start = max(1, min(24, current_day - 3))
        for day in range(start, start + 7):
            active = day == current_day
            chip = ctk.CTkFrame(strip, width=46, height=56, corner_radius=18, fg_color="#0E1226" if active else "#EFEFF5")
            chip.pack(side="left", padx=3)
            chip.pack_propagate(False)
            ctk.CTkLabel(chip, text=f"D{day}", font=("Segoe UI Semibold", 11), text_color="#F6F7FD" if active else "#73758A").pack(expand=True)

        stats = ctk.CTkFrame(self.content, fg_color="transparent")
        stats.pack(fill="x")
        stats.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkLabel(stats, text=f"Next: {self._next_task()}", font=("Segoe UI", 12), text_color="#21253D", wraplength=175, justify="left", fg_color="#F3F0FF", corner_radius=14).grid(row=0, column=0, sticky="nsew", padx=4, pady=4)
        ctk.CTkLabel(stats, text="\n".join(self.engine.get_daily_exercises()), font=("Segoe UI", 12), text_color="#21253D", wraplength=175, justify="left", fg_color="#EDF5FF", corner_radius=14).grid(row=0, column=1, sticky="nsew", padx=4, pady=4)

        ctk.CTkButton(self.content, text="Capture Bedtime Progress (Ghost Overlay)", height=42, corner_radius=14, fg_color="#101223", hover_color="#1C223A", font=("Segoe UI Semibold", 14), command=self.capture_progress_only).pack(fill="x", pady=(10, 0))
        if animate:
            self._animate_progress(self.hero_bar, progress / 100, 0)

    def _render_routine(self):
        self._render_header("Routine")
        ctk.CTkLabel(self.content, text="Mandatory proof tasks", font=("Bahnschrift SemiBold", 28), text_color="#1A1A27").pack(anchor="w", pady=(0, 8))
        ctk.CTkLabel(self.content, text="No on/off switch. Task completes only after proof capture.", font=("Segoe UI", 12), text_color="#5D6075").pack(anchor="w", pady=(0, 8))

        grid = ctk.CTkFrame(self.content, fg_color="transparent")
        grid.pack(fill="both", expand=True)
        for i in range(3):
            grid.grid_columnconfigure(i, weight=1)

        for index, task in enumerate(self.engine.get_tasks()):
            row, col = divmod(index, 3)
            done = bool(task.get("done"))
            card = ctk.CTkFrame(grid, fg_color="#D2ECD6" if done else self.CARD_COLORS[index], corner_radius=18)
            card.grid(row=row, column=col, sticky="nsew", padx=4, pady=4)
            ctk.CTkLabel(card, text="Done" if done else "Pending", font=("Segoe UI Semibold", 11), text_color="#2D8750" if done else "#5E6179").pack(anchor="w", padx=10, pady=(8, 0))
            ctk.CTkLabel(card, text=task.get("name"), font=("Bahnschrift SemiBold", 14), text_color="#13172D", wraplength=124, justify="left").pack(anchor="w", padx=10, pady=(2, 0))
            ctk.CTkLabel(card, text=f"Time: {task.get('target_time', '--:--')}", font=("Segoe UI", 10), text_color="#42455B").pack(anchor="w", padx=10, pady=(2, 0))
            ctk.CTkLabel(card, text=task.get("note", ""), font=("Segoe UI", 10), text_color="#484B60", wraplength=124, justify="left").pack(anchor="w", padx=10, pady=(2, 4))
            ctk.CTkButton(card, text="Retake Proof" if done else "Capture Proof", height=28, corner_radius=11, fg_color="#101224", hover_color="#1B2140", font=("Segoe UI Semibold", 10), command=lambda tid=task.get("id"): self.capture_task(tid)).pack(fill="x", padx=8, pady=(0, 4))
            if done:
                ctk.CTkButton(card, text="Reset", height=22, corner_radius=10, fg_color="#ECEAF4", hover_color="#DDD9E7", text_color="#2E324A", font=("Segoe UI", 10), command=lambda tid=task.get("id"): self.reset_task(tid)).pack(fill="x", padx=8, pady=(0, 8))
            else:
                ctk.CTkLabel(card, text="", height=22).pack(pady=(0, 8))

    def _render_guard(self):
        self._render_header("Guard")
        settings = self.engine.data.get("settings", {})
        panel = ctk.CTkFrame(self.content, fg_color="#F3F0FF", corner_radius=20)
        panel.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(panel, text="Guard Status", font=("Bahnschrift SemiBold", 24), text_color="#1D2035").pack(anchor="w", padx=14, pady=(12, 0))
        ctk.CTkLabel(panel, text=f"Morning gate: {'Unlocked' if self.engine.is_morning_ready() else 'Locked'}", font=("Segoe UI Semibold", 13), text_color="#2D8750" if self.engine.is_morning_ready() else "#C74444").pack(anchor="w", padx=14, pady=(6, 0))
        ctk.CTkLabel(panel, text=f"Sleep lock: {'ACTIVE' if self.engine.is_sleep_window_active() else 'Standby'} ({settings.get('sleep_lock_start')} -> {settings.get('sleep_lock_end')})", font=("Segoe UI Semibold", 13), text_color="#C74444" if self.engine.is_sleep_window_active() else "#5F6380").pack(anchor="w", padx=14, pady=(2, 10))
        ctk.CTkLabel(self.content, text="Blocked apps (one process per line)", font=("Segoe UI Semibold", 13), text_color="#2C2E45").pack(anchor="w", pady=(0, 4))
        self.guard_box = ctk.CTkTextbox(self.content, height=190, corner_radius=14)
        self.guard_box.pack(fill="x")
        self.guard_box.insert("1.0", "\n".join(sorted(self.guard.distractions)))
        ctk.CTkButton(self.content, text="Save Blocked App List", height=38, corner_radius=12, fg_color="#111328", hover_color="#202544", font=("Segoe UI Semibold", 13), command=self.save_guard_list).pack(fill="x", pady=(10, 0))

    def _render_vault(self):
        self._render_header("Vault")
        ctk.CTkLabel(self.content, text="Proof Vault", font=("Bahnschrift SemiBold", 28), text_color="#1A1A27").pack(anchor="w", pady=(0, 8))
        row = ctk.CTkFrame(self.content, fg_color="transparent")
        row.pack(fill="x", pady=(0, 8))
        ctk.CTkButton(row, text="Open Vault Folder", height=36, corner_radius=12, fg_color="#0F1224", hover_color="#1D2242", font=("Segoe UI Semibold", 12), command=self.open_vault).pack(side="left", fill="x", expand=True, padx=(0, 4))
        ctk.CTkButton(row, text="Capture Bedtime Progress", height=36, corner_radius=12, fg_color="#5E47B5", hover_color="#6C57C4", font=("Segoe UI Semibold", 12), command=self.capture_progress_only).pack(side="left", fill="x", expand=True, padx=(4, 0))
        box = ctk.CTkFrame(self.content, fg_color="#F3F0FF", corner_radius=16)
        box.pack(fill="both", expand=True)
        proofs = [t for t in self.engine.get_tasks() if t.get("proof_path")]
        if not proofs:
            ctk.CTkLabel(box, text="No proof files yet for today.", font=("Segoe UI", 13), text_color="#5E627A").pack(anchor="w", padx=14, pady=14)
            return
        for task in proofs[:9]:
            item = ctk.CTkFrame(box, fg_color="#FFFFFF", corner_radius=12)
            item.pack(fill="x", padx=10, pady=5)
            ctk.CTkLabel(item, text=task.get("name"), font=("Segoe UI Semibold", 12), text_color="#1C2037").pack(side="left", padx=10, pady=8)
            ctk.CTkLabel(item, text=task.get("completed_at", ""), font=("Segoe UI", 10), text_color="#5F637A").pack(side="left", padx=(0, 8), pady=8)
            ctk.CTkButton(item, text="Open", width=70, height=28, corner_radius=10, fg_color="#0E1222", hover_color="#1C2140", font=("Segoe UI", 11), command=lambda p=task.get("proof_path"): self.open_proof(p)).pack(side="right", padx=8, pady=6)

    def _render_settings(self):
        self._render_header("Settings")
        settings = self.engine.data.get("settings", {})
        panel = ctk.CTkFrame(self.content, fg_color="#F4F1FF", corner_radius=20)
        panel.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(panel, text="Discipline Settings", font=("Bahnschrift SemiBold", 26), text_color="#1F2238").pack(anchor="w", padx=14, pady=(12, 0))
        self.inputs = {}

        for key, label in (("sleep_lock_start", "Sleep lock start (HH:MM)"), ("sleep_lock_end", "Sleep lock end (HH:MM)"), ("weather_city", "Weather city for walk scan")):
            ctk.CTkLabel(panel, text=label, font=("Segoe UI", 12), text_color="#3F425B").pack(anchor="w", padx=14, pady=(8, 0))
            entry = ctk.CTkEntry(panel, height=34, corner_radius=10)
            entry.insert(0, settings.get(key, ""))
            entry.pack(fill="x", padx=14, pady=(2, 2))
            self.inputs[key] = entry

        toggles = ctk.CTkFrame(panel, fg_color="transparent")
        toggles.pack(fill="x", padx=14, pady=(6, 12))
        self.inputs["reminders_enabled"] = ctk.CTkSwitch(toggles, text="Reminders")
        self.inputs["reminders_enabled"].pack(side="left", padx=(0, 20))
        if settings.get("reminders_enabled", True):
            self.inputs["reminders_enabled"].select()
        self.inputs["sound_enabled"] = ctk.CTkSwitch(toggles, text="Sound")
        self.inputs["sound_enabled"].pack(side="left")
        if settings.get("sound_enabled", True):
            self.inputs["sound_enabled"].select()

        row = ctk.CTkFrame(self.content, fg_color="transparent")
        row.pack(fill="x")
        ctk.CTkButton(row, text="Save Settings", height=38, corner_radius=12, fg_color="#101223", hover_color="#202744", font=("Segoe UI Semibold", 12), command=self.save_settings).pack(side="left", fill="x", expand=True, padx=(0, 4))
        ctk.CTkButton(row, text="Refresh Weather", height=38, corner_radius=12, fg_color="#5C49B4", hover_color="#6D59C2", font=("Segoe UI Semibold", 12), command=self.refresh_weather_async).pack(side="left", fill="x", expand=True, padx=(4, 0))
        ctk.CTkButton(self.content, text="Reset Today's Tasks", height=38, corner_radius=12, fg_color="#ECEAF4", hover_color="#DDD9E7", text_color="#2E324A", font=("Segoe UI Semibold", 12), command=self.reset_today).pack(fill="x", pady=(8, 0))

    def _render_navbar(self):
        for tab in self.TABS:
            active = tab == self.active_tab
            ctk.CTkButton(
                self.navbar,
                text=tab,
                width=72,
                height=36,
                corner_radius=18,
                fg_color="#F7F7FB" if active else "transparent",
                hover_color="#2A2E45" if not active else "#F7F7FB",
                text_color="#0E1225" if active else "#A8A9BC",
                font=("Segoe UI Semibold", 11),
                command=lambda t=tab: self.switch_tab(t),
            ).pack(side="left", expand=True, padx=2, pady=10)

    def _animate_progress(self, bar, target, frame):
        steps = 18
        bar.set(min(target, target * (frame / steps)))
        if frame >= steps:
            bar.set(target)
            return
        self.after(24, lambda: self._animate_progress(bar, target, frame + 1))

    def _next_task(self):
        pending = [task for task in self.engine.get_tasks() if not task.get("done")]
        if not pending:
            return "All tasks complete."
        pending.sort(key=lambda t: t.get("target_time", "99:99"))
        nxt = pending[0]
        return f"{nxt.get('target_time')} - {nxt.get('name')}"

    def capture_task(self, task_id):
        task = self.engine.get_task(task_id)
        if not task:
            return
        proof_path = self.vision.capture_task_proof(self.engine.data.get("day", 1), task_id, task.get("name", f"task_{task_id}"), with_overlay=(task_id == 9))
        if not proof_path:
            return
        self.engine.mark_task_with_proof(task_id, proof_path)
        self.render_tab(animate=False)

    def capture_progress_only(self, refresh=True):
        if self.vision.capture_progress(self.engine.data.get("day", 1)) and refresh:
            self.render_tab(animate=False)

    def reset_task(self, task_id):
        self.engine.reset_task(task_id)
        self.render_tab(animate=False)

    def save_guard_list(self):
        names = [line.strip().lower() for line in self.guard_box.get("1.0", "end").splitlines() if line.strip()]
        self.guard.set_distractions(names)
        self.render_tab(animate=False)

    def open_vault(self):
        try:
            os.startfile(os.path.abspath(self.vision.vault))
        except Exception:
            pass

    def open_proof(self, proof_path):
        if proof_path and os.path.exists(proof_path):
            try:
                os.startfile(proof_path)
            except Exception:
                pass

    def save_settings(self):
        self.engine.update_setting("sleep_lock_start", self.inputs["sleep_lock_start"].get().strip())
        self.engine.update_setting("sleep_lock_end", self.inputs["sleep_lock_end"].get().strip())
        self.engine.update_setting("weather_city", self.inputs["weather_city"].get().strip() or "Manila")
        self.engine.update_setting("reminders_enabled", bool(self.inputs["reminders_enabled"].get()))
        self.engine.update_setting("sound_enabled", bool(self.inputs["sound_enabled"].get()))
        self.refresh_weather_async()
        self.render_tab(animate=False)

    def reset_today(self):
        self.engine.reset_all_tasks_for_today()
        self.render_tab(animate=False)

    def _lock_tick(self):
        sleep_active = self.engine.is_sleep_window_active()
        self.guard.enforce_lockout(force=sleep_active)
        if sleep_active:
            self._show_sleep_lock()
        else:
            self._hide_sleep_lock()
        self.after(5000, self._lock_tick)

    def _show_sleep_lock(self):
        if self.sleep_lock_window is None:
            self.sleep_lock_window = ctk.CTkToplevel(self)
            self.sleep_lock_window.title("Sleep Lock Active")
            self.sleep_lock_window.attributes("-fullscreen", True)
            self.sleep_lock_window.attributes("-topmost", True)
            self.sleep_lock_window.protocol("WM_DELETE_WINDOW", lambda: None)
            self.sleep_lock_window.configure(fg_color="#090B14")
            ctk.CTkLabel(self.sleep_lock_window, text="SLEEP LOCK ACTIVE", font=("Bahnschrift SemiBold", 58), text_color="#F1F2FF").pack(pady=(120, 16))
            ctk.CTkLabel(self.sleep_lock_window, text="Distraction lock is active.\nRecover and sleep now.", font=("Segoe UI", 22), text_color="#A8AECF", justify="center").pack()
            self.sleep_lock_label = ctk.CTkLabel(self.sleep_lock_window, text="", font=("Segoe UI Semibold", 24), text_color="#C9CEEE")
            self.sleep_lock_label.pack(pady=(16, 0))
        self.sleep_lock_window.lift()
        self.sleep_lock_window.focus_force()
        unlock_time = self._next_unlock()
        left = max(0, int((unlock_time - datetime.now()).total_seconds() // 60))
        self.sleep_lock_label.configure(text=f"Unlocks at {unlock_time.strftime('%H:%M')} ({left // 60:02d}h {left % 60:02d}m remaining)")

    def _hide_sleep_lock(self):
        if self.sleep_lock_window is not None:
            self.sleep_lock_window.destroy()
            self.sleep_lock_window = None
            self.sleep_lock_label = None

    def _next_unlock(self):
        end_text = self.engine.data.get("settings", {}).get("sleep_lock_end", "05:00")
        hour, minute = [int(piece) for piece in end_text.split(":")]
        now = datetime.now()
        unlock = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if unlock <= now:
            unlock += timedelta(days=1)
        return unlock

    def _reminder_tick(self):
        if self.engine.data.get("settings", {}).get("reminders_enabled", True):
            now = datetime.now().strftime("%H:%M")
            today = datetime.now().strftime("%Y-%m-%d")
            for task in self.engine.get_tasks():
                if task.get("done") or task.get("target_time") != now:
                    continue
                key = f"{today}:{task.get('id')}:{now}"
                if key in self.reminder_keys:
                    continue
                self.reminder_keys.add(key)
                self._notify(task)
        self.after(30000, self._reminder_tick)

    def _notify(self, task):
        if self.engine.data.get("settings", {}).get("sound_enabled", True) and winsound is not None:
            try:
                winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
            except RuntimeError:
                pass
        pop = ctk.CTkToplevel(self)
        pop.title("Task Reminder")
        pop.geometry("360x200")
        pop.attributes("-topmost", True)
        pop.configure(fg_color="#F3F1FF")
        ctk.CTkLabel(pop, text="Reminder", font=("Bahnschrift SemiBold", 28), text_color="#1A1E34").pack(anchor="w", padx=16, pady=(12, 2))
        ctk.CTkLabel(pop, text=f"{task.get('target_time')} - {task.get('name')}", font=("Segoe UI Semibold", 14), text_color="#2F3450").pack(anchor="w", padx=16)
        ctk.CTkLabel(pop, text="Capture proof now to keep the lockout moving.", font=("Segoe UI", 12), text_color="#575C77").pack(anchor="w", padx=16, pady=(8, 12))
        ctk.CTkButton(pop, text="Capture Proof", height=34, corner_radius=10, fg_color="#101224", hover_color="#1D2240", command=lambda tid=task.get("id"), win=pop: self._capture_from_popup(tid, win)).pack(fill="x", padx=16, pady=(0, 6))
        ctk.CTkButton(pop, text="Dismiss", height=28, corner_radius=10, fg_color="#E7E4F2", hover_color="#DCD8EA", text_color="#32364E", command=pop.destroy).pack(fill="x", padx=16)

    def _capture_from_popup(self, task_id, pop):
        pop.destroy()
        self.capture_task(task_id)

    def _weather_tick(self):
        self.refresh_weather_async()
        self.after(3600000, self._weather_tick)

    def refresh_weather_async(self):
        if self.weather_loading:
            return
        self.weather_loading = True
        city = self.engine.data.get("settings", {}).get("weather_city", "Manila")
        threading.Thread(target=self._weather_worker, args=(city,), daemon=True).start()

    def _weather_worker(self, city):
        result = self._fetch_weather(city)
        self.after(0, lambda: self._apply_weather(*result))

    def _fetch_weather(self, city):
        safe_city = urllib.parse.quote(city or "Manila")
        url = f"https://wttr.in/{safe_city}?format=j1"
        try:
            with urllib.request.urlopen(url, timeout=6) as response:
                payload = response.read().decode("utf-8")
            weather_data = json.loads(payload)
            current = weather_data.get("current_condition", [{}])[0]
            desc = current.get("weatherDesc", [{"value": "Unknown"}])[0].get("value", "Unknown")
            hourly = weather_data.get("weather", [{}])[0].get("hourly", [])
            five_am = min(hourly, key=lambda h: abs(int(h.get("time", "0")) - 500)) if hourly else {}
            rain = int(five_am.get("chanceofrain", 0))
            bad = rain >= 60 or any(word in str(desc).lower() for word in ("rain", "storm", "thunder"))
            if bad:
                return (False, f"5AM rough ({desc}, rain {rain}%). Indoor fallback activated.")
            return (True, f"5AM workable ({desc}, rain {rain}%). Outdoor walk approved.")
        except (urllib.error.URLError, TimeoutError, ValueError, KeyError, OSError):
            return (True, "Weather scan unavailable (offline). Default outdoor schedule kept.")

    def _apply_weather(self, good_for_walk, summary):
        self.weather_loading = False
        self.engine.apply_weather_result(good_for_walk, summary)
        if self.active_tab in {"Home", "Routine", "Settings"}:
            self.render_tab(animate=False)


if __name__ == "__main__":
    app = GlowApp()
    app.mainloop()
