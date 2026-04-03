import json
import threading
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta

from kivy.animation import Animation
from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, RoundedRectangle
from kivy.metrics import dp
from kivy.properties import NumericProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.modalview import ModalView
from kivy.uix.popup import Popup
from kivy.uix.progressbar import ProgressBar
from kivy.uix.screenmanager import Screen, ScreenManager, SlideTransition
from kivy.uix.scrollview import ScrollView
from kivy.uix.switch import Switch
from kivy.uix.textinput import TextInput
from kivy.utils import get_color_from_hex

from engine_mobile import MobileGlowEngine
from vision_mobile import MobileVision

try:
    from plyer import notification
except Exception:
    notification = None


Window.clearcolor = get_color_from_hex("#CEC2E9")


def color(hex_value):
    return get_color_from_hex(hex_value)


def style_button(button, bg_hex, fg_hex="#101223"):
    button.background_normal = ""
    button.background_down = ""
    button.background_color = color(bg_hex)
    button.color = color(fg_hex)


def bind_rounded_background(widget, hex_color, radius=18):
    rgba = color(hex_color)
    with widget.canvas.before:
        widget._bg_color = Color(*rgba)
        widget._bg_rect = RoundedRectangle(pos=widget.pos, size=widget.size, radius=[radius])

    def update_rect(*_args):
        widget._bg_rect.pos = widget.pos
        widget._bg_rect.size = widget.size

    widget.bind(pos=update_rect, size=update_rect)


class SplashScreen(Screen):
    progress_value = NumericProperty(0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        root = BoxLayout(orientation="vertical", padding=[dp(18), dp(20), dp(18), dp(20)])
        bind_rounded_background(root, "#101223", radius=22)
        self.add_widget(root)

        root.add_widget(Label(size_hint_y=0.22))
        title = Label(text="RDP Glow", font_size="42sp", bold=True, color=color("#F4F4FF"), size_hint_y=None, height=dp(70))
        subtitle = Label(text="Discipline Console", font_size="16sp", color=color("#A5A9C8"), size_hint_y=None, height=dp(32))
        root.add_widget(title)
        root.add_widget(subtitle)
        root.add_widget(Label(size_hint_y=0.05))

        self.bar = ProgressBar(max=100, value=0, size_hint_y=None, height=dp(12))
        root.add_widget(self.bar)
        root.add_widget(Label(size_hint_y=0.73))

    def on_enter(self, *_args):
        self.progress_value = 0
        Clock.schedule_interval(self._tick, 0.03)

    def _tick(self, _dt):
        self.progress_value += 2.9
        self.bar.value = min(100, self.progress_value)
        if self.progress_value >= 100:
            Clock.schedule_once(self._finish, 0.15)
            return False
        return True

    def _finish(self, _dt):
        if self.manager:
            self.manager.transition = SlideTransition(direction="left", duration=0.35)
            self.manager.current = "main"


class MainScreen(Screen):
    def __init__(self, engine, vision, **kwargs):
        super().__init__(**kwargs)
        self.ui = MobileDashboard(engine=engine, vision=vision)
        self.add_widget(self.ui)


class MobileDashboard(BoxLayout):
    TABS = ("Home", "Routine", "Guard", "Vault", "Settings")
    CARD_COLORS = ("#FFD36B", "#BFD7FF", "#FFBEE8", "#BEF2D5", "#FFD9A8", "#BBD9FF", "#E3CEFF", "#AEEED5", "#D8D3FF")

    def __init__(self, engine, vision, **kwargs):
        super().__init__(orientation="vertical", padding=[dp(10), dp(10), dp(10), dp(10)], spacing=dp(8), **kwargs)
        self.engine = engine
        self.vision = vision
        self.current_tab = "Home"
        self.reminder_keys = set()
        self.weather_loading = False
        self.sleep_modal = None
        self.sleep_countdown_label = None
        self.settings_inputs = {}

        body = BoxLayout(orientation="vertical", spacing=dp(8))
        bind_rounded_background(body, "#F7F7FB", radius=20)
        self.add_widget(body)

        self.header = BoxLayout(size_hint_y=None, height=dp(70), spacing=dp(8), padding=[dp(6), dp(6), dp(6), dp(0)])
        body.add_widget(self.header)

        self.content = BoxLayout(orientation="vertical", spacing=dp(8), padding=[dp(2), dp(0), dp(2), dp(0)])
        body.add_widget(self.content)

        self.navbar = BoxLayout(size_hint_y=None, height=dp(58), spacing=dp(6), padding=[dp(6), dp(8), dp(6), dp(8)])
        bind_rounded_background(self.navbar, "#101223", radius=18)
        body.add_widget(self.navbar)

        self.render_tab(animate=True)

        Clock.schedule_interval(self._lock_tick, 5)
        Clock.schedule_interval(self._reminder_tick, 30)
        Clock.schedule_interval(self._weather_interval_tick, 3600)
        self.refresh_weather_async()

    def clear_box(self, box):
        box.clear_widgets()

    def render_header(self, subtitle):
        self.clear_box(self.header)

        avatar = Label(
            text="R",
            bold=True,
            color=color("#F7F7FB"),
            size_hint=(None, None),
            size=(dp(46), dp(46)),
            halign="center",
            valign="middle",
        )
        bind_rounded_background(avatar, "#11142A", radius=23)

        info = BoxLayout(orientation="vertical", spacing=0)
        info.add_widget(Label(text="Hello, Champion", font_size="20sp", bold=True, color=color("#1B1E33"), halign="left", valign="middle"))
        day = self.engine.data.get("day", 1)
        info.add_widget(Label(text=f"Day {day} | {datetime.now().strftime('%a, %d %b %Y')} | {subtitle}", font_size="12sp", color=color("#6A6B7D"), halign="left", valign="middle"))

        self.header.add_widget(avatar)
        self.header.add_widget(info)

    def render_tab(self, animate=False):
        self.clear_box(self.content)
        if self.current_tab == "Home":
            self.render_home(animate=animate)
        elif self.current_tab == "Routine":
            self.render_routine()
        elif self.current_tab == "Guard":
            self.render_guard()
        elif self.current_tab == "Vault":
            self.render_vault()
        else:
            self.render_settings()
        self.render_navbar()

    def render_home(self, animate=False):
        self.render_header("Home")
        tasks = self.engine.get_tasks()
        progress = self.engine.get_progress()
        completed = self.engine.count_completed()
        weather_summary = self.engine.data.get("weather", {}).get("summary", "Weather not checked.")

        hero = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(190), padding=[dp(14), dp(14), dp(14), dp(14)], spacing=dp(8))
        bind_rounded_background(hero, "#8D7AFC", radius=22)
        hero.add_widget(Label(text="Daily challenge", font_size="36sp", bold=True, color=color("#10112B"), size_hint_y=None, height=dp(54), halign="left", valign="middle"))
        gate_text = "Guard active until Morning Water + Jog are proved." if not self.engine.is_morning_ready() else "Morning gate unlocked. Keep momentum high."
        hero.add_widget(Label(text=gate_text, font_size="12sp", color=color("#1F2040"), size_hint_y=None, height=dp(20), halign="left", valign="middle"))
        hero.add_widget(Label(text=f"Weather: {weather_summary}", font_size="11sp", color=color("#2B2D52"), size_hint_y=None, height=dp(34), halign="left", valign="top"))

        self.hero_bar = ProgressBar(max=100, value=0 if animate else progress, size_hint_y=None, height=dp(10))
        hero.add_widget(self.hero_bar)
        hero.add_widget(Label(text=f"{progress}% complete | {completed}/{len(tasks)} proofs submitted", font_size="12sp", bold=True, color=color("#1E2243"), size_hint_y=None, height=dp(22), halign="left", valign="middle"))
        self.content.add_widget(hero)

        if animate:
            Animation.cancel_all(self.hero_bar, "value")
            Animation(value=progress, duration=0.5, t="out_cubic").start(self.hero_bar)

        strip = BoxLayout(size_hint_y=None, height=dp(58), spacing=dp(4))
        current_day = self.engine.data.get("day", 1)
        start = max(1, min(24, current_day - 3))
        for day in range(start, start + 7):
            active = day == current_day
            chip = Label(text=f"D{day}", font_size="11sp", bold=True, color=color("#F6F7FD" if active else "#73758A"), size_hint=(None, None), size=(dp(44), dp(56)))
            bind_rounded_background(chip, "#0E1226" if active else "#EFEFF5", radius=16)
            strip.add_widget(chip)
        self.content.add_widget(strip)

        row = BoxLayout(size_hint_y=None, height=dp(120), spacing=dp(8))
        next_card = BoxLayout(orientation="vertical", padding=[dp(10), dp(8), dp(10), dp(8)])
        bind_rounded_background(next_card, "#F3F0FF", radius=18)
        next_card.add_widget(Label(text="Next up", font_size="13sp", bold=True, color=color("#3C3E57"), size_hint_y=None, height=dp(24), halign="left"))
        next_card.add_widget(Label(text=self.next_task_text(), font_size="12sp", color=color("#1D2034"), halign="left", valign="top"))
        row.add_widget(next_card)

        workout_card = BoxLayout(orientation="vertical", padding=[dp(10), dp(8), dp(10), dp(8)])
        bind_rounded_background(workout_card, "#EDF7FF", radius=18)
        workout_card.add_widget(Label(text="Workout today", font_size="13sp", bold=True, color=color("#3C3E57"), size_hint_y=None, height=dp(24), halign="left"))
        workout_card.add_widget(Label(text="\n".join(self.engine.get_daily_exercises()), font_size="11sp", color=color("#1D2034"), halign="left", valign="top"))
        row.add_widget(workout_card)
        self.content.add_widget(row)

        bedtime_btn = Button(text="Capture Bedtime Progress (Ghost Overlay)", size_hint_y=None, height=dp(44), bold=True)
        style_button(bedtime_btn, "#101223", "#F2F3FE")
        bedtime_btn.bind(on_release=lambda *_: self.capture_progress_only())
        self.content.add_widget(bedtime_btn)

    def render_routine(self):
        self.render_header("Routine")
        title = Label(text="Mandatory proof tasks", font_size="28sp", bold=True, color=color("#1A1A27"), size_hint_y=None, height=dp(40), halign="left")
        subtitle = Label(text="No on/off toggle. Task is done only after proof capture.", font_size="12sp", color=color("#5D6075"), size_hint_y=None, height=dp(24), halign="left")
        self.content.add_widget(title)
        self.content.add_widget(subtitle)

        scroll = ScrollView(do_scroll_x=False, do_scroll_y=True, bar_width=0)
        grid = GridLayout(cols=2, spacing=dp(6), size_hint_y=None)
        grid.bind(minimum_height=grid.setter("height"))

        for index, task in enumerate(self.engine.get_tasks()):
            card = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(208), padding=[dp(8), dp(8), dp(8), dp(8)], spacing=dp(4))
            done = bool(task.get("done"))
            card_color = "#D2ECD6" if done else self.CARD_COLORS[index % len(self.CARD_COLORS)]
            bind_rounded_background(card, card_color, radius=16)
            card.add_widget(Label(text="Done" if done else "Pending", font_size="11sp", bold=True, color=color("#2D8750" if done else "#5E6179"), size_hint_y=None, height=dp(18), halign="left"))
            card.add_widget(Label(text=task.get("name"), font_size="14sp", bold=True, color=color("#13172D"), size_hint_y=None, height=dp(42), halign="left"))
            card.add_widget(Label(text=f"Time: {task.get('target_time', '--:--')}", font_size="11sp", color=color("#42455B"), size_hint_y=None, height=dp(18), halign="left"))
            card.add_widget(Label(text=task.get("note", ""), font_size="10sp", color=color("#484B60"), size_hint_y=None, height=dp(58), halign="left", valign="top"))

            capture = Button(text="Retake Proof" if done else "Capture Proof", size_hint_y=None, height=dp(30), bold=True)
            style_button(capture, "#101224", "#F2F3FE")
            capture.bind(on_release=lambda *_args, task_id=task.get("id"): self.capture_task(task_id))
            card.add_widget(capture)

            if done:
                reset = Button(text="Reset", size_hint_y=None, height=dp(24))
                style_button(reset, "#ECEAF4", "#2E324A")
                reset.bind(on_release=lambda *_args, task_id=task.get("id"): self.reset_task(task_id))
                card.add_widget(reset)
            else:
                card.add_widget(Label(size_hint_y=None, height=dp(24)))

            grid.add_widget(card)

        scroll.add_widget(grid)
        self.content.add_widget(scroll)

    def render_guard(self):
        self.render_header("Guard")
        settings = self.engine.data.get("settings", {})

        panel = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(176), padding=[dp(12), dp(12), dp(12), dp(12)], spacing=dp(6))
        bind_rounded_background(panel, "#F3F0FF", radius=18)
        panel.add_widget(Label(text="Guard Status", font_size="24sp", bold=True, color=color("#1D2035"), size_hint_y=None, height=dp(32), halign="left"))
        panel.add_widget(Label(text=f"Morning gate: {'Unlocked' if self.engine.is_morning_ready() else 'Locked'}", font_size="13sp", bold=True, color=color("#2D8750" if self.engine.is_morning_ready() else "#C74444"), size_hint_y=None, height=dp(22), halign="left"))
        panel.add_widget(Label(text=f"Sleep lock: {'ACTIVE' if self.engine.is_sleep_window_active() else 'Standby'}", font_size="13sp", bold=True, color=color("#C74444" if self.engine.is_sleep_window_active() else "#5F6380"), size_hint_y=None, height=dp(22), halign="left"))
        panel.add_widget(Label(text=f"Window: {settings.get('sleep_lock_start')} -> {settings.get('sleep_lock_end')}", font_size="12sp", color=color("#595E7C"), size_hint_y=None, height=dp(20), halign="left"))
        panel.add_widget(Label(text="Android note: apps cannot force-kill other apps without device-owner privileges.", font_size="11sp", color=color("#575C77"), halign="left", valign="top"))
        self.content.add_widget(panel)

        info = Label(
            text="Use strict reminders + sleep lock overlay for discipline mode. For stronger lock, enable kiosk mode with a dedicated launcher.",
            font_size="12sp",
            color=color("#353A58"),
            halign="left",
            valign="top",
        )
        self.content.add_widget(info)

    def render_vault(self):
        self.render_header("Vault")
        title = Label(text="Proof Vault", font_size="28sp", bold=True, color=color("#1A1A27"), size_hint_y=None, height=dp(42), halign="left")
        self.content.add_widget(title)

        capture_btn = Button(text="Capture Bedtime Progress", size_hint_y=None, height=dp(42), bold=True)
        style_button(capture_btn, "#5E47B5", "#F5F1FF")
        capture_btn.bind(on_release=lambda *_: self.capture_progress_only())
        self.content.add_widget(capture_btn)

        scroll = ScrollView(do_scroll_x=False, do_scroll_y=True, bar_width=0)
        wrap = GridLayout(cols=1, spacing=dp(6), size_hint_y=None, padding=[0, dp(8), 0, dp(8)])
        wrap.bind(minimum_height=wrap.setter("height"))

        proofs = [task for task in self.engine.get_tasks() if task.get("proof_path")]
        if not proofs:
            empty = Label(text="No proof files yet for today.", font_size="13sp", color=color("#5E627A"), size_hint_y=None, height=dp(36), halign="left")
            wrap.add_widget(empty)
        else:
            for task in proofs:
                item = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(82), padding=[dp(10), dp(8), dp(10), dp(8)], spacing=dp(2))
                bind_rounded_background(item, "#F1EEFF", radius=14)
                proof_path = task.get("proof_path", "")
                filename = proof_path.split("/")[-1].split("\\")[-1] if proof_path else ""
                item.add_widget(Label(text=task.get("name"), font_size="13sp", bold=True, color=color("#1C2037"), size_hint_y=None, height=dp(22), halign="left"))
                item.add_widget(Label(text=task.get("completed_at", ""), font_size="11sp", color=color("#5F637A"), size_hint_y=None, height=dp(18), halign="left"))
                item.add_widget(Label(text=filename, font_size="10sp", color=color("#6B6F86"), halign="left", valign="middle"))
                wrap.add_widget(item)

        scroll.add_widget(wrap)
        self.content.add_widget(scroll)

    def render_settings(self):
        self.render_header("Settings")
        settings = self.engine.data.get("settings", {})
        self.settings_inputs = {}

        card = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(320), padding=[dp(12), dp(10), dp(12), dp(10)], spacing=dp(8))
        bind_rounded_background(card, "#F4F1FF", radius=18)
        card.add_widget(Label(text="Discipline Settings", font_size="25sp", bold=True, color=color("#1F2238"), size_hint_y=None, height=dp(34), halign="left"))

        self.settings_inputs["sleep_lock_start"] = self._labeled_input(card, "Sleep lock start (HH:MM)", settings.get("sleep_lock_start", "21:00"))
        self.settings_inputs["sleep_lock_end"] = self._labeled_input(card, "Sleep lock end (HH:MM)", settings.get("sleep_lock_end", "05:00"))
        self.settings_inputs["weather_city"] = self._labeled_input(card, "Weather city for walk scan", settings.get("weather_city", "Manila"))

        toggles = BoxLayout(size_hint_y=None, height=dp(36), spacing=dp(16))
        rem_lbl = Label(text="Reminders", font_size="12sp", color=color("#3F425B"), halign="left")
        rem_switch = Switch(active=bool(settings.get("reminders_enabled", True)))
        snd_lbl = Label(text="Sound", font_size="12sp", color=color("#3F425B"), halign="left")
        snd_switch = Switch(active=bool(settings.get("sound_enabled", True)))
        toggles.add_widget(rem_lbl)
        toggles.add_widget(rem_switch)
        toggles.add_widget(snd_lbl)
        toggles.add_widget(snd_switch)
        self.settings_inputs["reminders_enabled"] = rem_switch
        self.settings_inputs["sound_enabled"] = snd_switch
        card.add_widget(toggles)
        self.content.add_widget(card)

        row = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(6))
        save = Button(text="Save Settings", bold=True)
        style_button(save, "#101223", "#F2F3FE")
        save.bind(on_release=lambda *_: self.save_settings())
        refresh = Button(text="Refresh Weather", bold=True)
        style_button(refresh, "#5C49B4", "#F5F1FF")
        refresh.bind(on_release=lambda *_: self.refresh_weather_async())
        row.add_widget(save)
        row.add_widget(refresh)
        self.content.add_widget(row)

        reset = Button(text="Reset Today's Tasks", size_hint_y=None, height=dp(40), bold=True)
        style_button(reset, "#ECEAF4", "#2E324A")
        reset.bind(on_release=lambda *_: self.reset_today())
        self.content.add_widget(reset)

    def _labeled_input(self, parent, title, value):
        parent.add_widget(Label(text=title, font_size="12sp", color=color("#3F425B"), size_hint_y=None, height=dp(20), halign="left"))
        field = TextInput(text=value, multiline=False, size_hint_y=None, height=dp(36), padding=[dp(10), dp(9), dp(10), dp(9)])
        parent.add_widget(field)
        return field

    def render_navbar(self):
        self.clear_box(self.navbar)
        for tab in self.TABS:
            active = tab == self.current_tab
            btn = Button(text=tab, font_size="11sp", bold=True)
            style_button(btn, "#F7F7FB" if active else "#101223", "#101223" if active else "#A8A9BC")
            btn.bind(on_release=lambda *_args, selected=tab: self.on_tab(selected))
            self.navbar.add_widget(btn)

    def on_tab(self, tab):
        self.current_tab = tab
        self.render_tab(animate=False)

    def next_task_text(self):
        pending = [task for task in self.engine.get_tasks() if not task.get("done")]
        if not pending:
            return "All mandatory tasks complete."
        pending.sort(key=lambda t: t.get("target_time", "99:99"))
        nxt = pending[0]
        return f"{nxt.get('target_time')} - {nxt.get('name')}"

    def show_popup(self, title, text):
        popup = Popup(title=title, content=Label(text=text, halign="center"), size_hint=(0.82, 0.35), auto_dismiss=True)
        popup.open()

    def capture_task(self, task_id):
        task = self.engine.get_task(task_id)
        if not task:
            return
        self.vision.capture_task_proof(
            day_number=self.engine.data.get("day", 1),
            task_id=task_id,
            task_name=task.get("name", f"task_{task_id}"),
            on_done=lambda path: self._on_capture_done(task_id, path),
        )

    def _on_capture_done(self, task_id, proof_path):
        def _finish(_dt):
            if proof_path:
                self.engine.mark_task_with_proof(task_id, proof_path)
                if task_id == 9:
                    self.capture_progress_only(show_message=False)
                self.render_tab(animate=False)
            else:
                self.show_popup("Capture Failed", "No image captured. Try again.")

        Clock.schedule_once(_finish, 0)

    def capture_progress_only(self, show_message=True):
        self.vision.capture_progress(
            day_number=self.engine.data.get("day", 1),
            on_done=lambda path: Clock.schedule_once(
                lambda _dt: self.show_popup("Progress Saved", "Bedtime progress captured.") if (path and show_message) else None,
                0,
            ),
        )

    def reset_task(self, task_id):
        self.engine.reset_task(task_id)
        self.render_tab(animate=False)

    def reset_today(self):
        self.engine.reset_all_tasks_for_today()
        self.render_tab(animate=False)

    def save_settings(self):
        self.engine.update_setting("sleep_lock_start", self.settings_inputs["sleep_lock_start"].text.strip())
        self.engine.update_setting("sleep_lock_end", self.settings_inputs["sleep_lock_end"].text.strip())
        self.engine.update_setting("weather_city", self.settings_inputs["weather_city"].text.strip() or "Manila")
        self.engine.update_setting("reminders_enabled", bool(self.settings_inputs["reminders_enabled"].active))
        self.engine.update_setting("sound_enabled", bool(self.settings_inputs["sound_enabled"].active))
        self.refresh_weather_async()
        self.show_popup("Saved", "Settings updated.")
        self.render_tab(animate=False)

    def _lock_tick(self, _dt):
        if self.engine.is_sleep_window_active():
            self.show_sleep_lock()
        else:
            self.hide_sleep_lock()
        return True

    def show_sleep_lock(self):
        if self.sleep_modal is None:
            modal = ModalView(size_hint=(1, 1), auto_dismiss=False)
            body = BoxLayout(orientation="vertical", padding=[dp(18), dp(28), dp(18), dp(28)], spacing=dp(10))
            bind_rounded_background(body, "#090B14", radius=0)
            body.add_widget(Label(text="SLEEP LOCK ACTIVE", font_size="44sp", bold=True, color=color("#F1F2FF"), size_hint_y=0.35))
            body.add_widget(Label(text="Distraction lock is active.\nRecover and sleep now.", font_size="20sp", color=color("#A8AECF"), size_hint_y=0.25))
            self.sleep_countdown_label = Label(text="", font_size="22sp", bold=True, color=color("#C9CEEE"), size_hint_y=0.2)
            body.add_widget(self.sleep_countdown_label)
            body.add_widget(Label(text="Unlocks automatically at your configured wake time.", font_size="13sp", color=color("#7880A8"), size_hint_y=0.2))
            modal.add_widget(body)
            self.sleep_modal = modal
            self.sleep_modal.open()

        unlock_dt = self.next_unlock_time()
        mins = max(0, int((unlock_dt - datetime.now()).total_seconds() // 60))
        self.sleep_countdown_label.text = f"Unlocks at {unlock_dt.strftime('%H:%M')} ({mins // 60:02d}h {mins % 60:02d}m)"

    def hide_sleep_lock(self):
        if self.sleep_modal is not None:
            self.sleep_modal.dismiss()
            self.sleep_modal = None
            self.sleep_countdown_label = None

    def next_unlock_time(self):
        end_text = self.engine.data.get("settings", {}).get("sleep_lock_end", "05:00")
        hour, minute = [int(piece) for piece in end_text.split(":")]
        now = datetime.now()
        unlock = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if unlock <= now:
            unlock += timedelta(days=1)
        return unlock

    def _reminder_tick(self, _dt):
        settings = self.engine.data.get("settings", {})
        if not settings.get("reminders_enabled", True):
            return True

        now = datetime.now().strftime("%H:%M")
        today = datetime.now().strftime("%Y-%m-%d")
        for task in self.engine.get_tasks():
            if task.get("done") or task.get("target_time") != now:
                continue
            key = f"{today}:{task.get('id')}:{now}"
            if key in self.reminder_keys:
                continue
            self.reminder_keys.add(key)
            self.send_reminder(task)
        return True

    def send_reminder(self, task):
        title = "RDP Glow Reminder"
        message = f"{task.get('target_time')} - {task.get('name')} needs proof capture."
        if notification is not None:
            try:
                notification.notify(title=title, message=message, app_name="RDP Glow", timeout=8)
            except Exception:
                pass
        self.show_popup("Task Reminder", message)

    def _weather_interval_tick(self, _dt):
        self.refresh_weather_async()
        return True

    def refresh_weather_async(self):
        if self.weather_loading:
            return
        self.weather_loading = True
        city = self.engine.data.get("settings", {}).get("weather_city", "Manila")
        thread = threading.Thread(target=self._weather_worker, args=(city,), daemon=True)
        thread.start()

    def _weather_worker(self, city):
        result = self.fetch_weather(city)
        Clock.schedule_once(lambda _dt: self.apply_weather(*result), 0)

    def fetch_weather(self, city):
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

    def apply_weather(self, good_for_walk, summary):
        self.weather_loading = False
        self.engine.apply_weather_result(good_for_walk, summary)
        if self.current_tab in {"Home", "Routine", "Settings"}:
            self.render_tab(animate=False)


class RDPGlowMobileApp(App):
    def build(self):
        data_file = f"{self.user_data_dir}/data.json"
        vault_folder = f"{self.user_data_dir}/glowup_vault"

        engine = MobileGlowEngine(data_path=data_file)
        vision = MobileVision(vault_path=vault_folder)

        manager = ScreenManager()
        manager.add_widget(SplashScreen(name="splash"))
        manager.add_widget(MainScreen(name="main", engine=engine, vision=vision))
        manager.current = "splash"
        return manager


if __name__ == "__main__":
    RDPGlowMobileApp().run()
