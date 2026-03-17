"""
main.py - GUI for Heartopia macro bot.
CLI flags: --dry-run  (print actions, no real input)
"""
import sys
import threading
import time
import customtkinter as ctk
import pygetwindow as gw

from src.player import Player
from src.recorder import Recorder
from src.logger import get_logger, get_log_file

MACRO_PATH = "route_macro.json"
WINDOW_TITLE_KEYWORD = "Heartopia"
DRY_RUN = "--dry-run" in sys.argv

logger = get_logger()

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


def focus_game_window():
    wins = [w for w in gw.getAllWindows()
            if WINDOW_TITLE_KEYWORD.lower() in w.title.lower()]
    if not wins:
        logger.warning(f"Window '{WINDOW_TITLE_KEYWORD}' not found.")
        return False
    try:
        wins[0].activate()
        time.sleep(0.5)
        logger.info(f"Focused: {wins[0].title}")
        return True
    except Exception as e:
        logger.error(f"Could not focus window: {e}")
        return False


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Heartopia Bot" + (" [DRY RUN]" if DRY_RUN else ""))
        self.geometry("420x320")
        self.resizable(False, False)

        self._state = "idle"
        self._build_ui()
        self._new_player()

    # ------------------------------------------------------------------ #
    def _new_player(self):
        speed = self.speed_var.get()
        self.player = Player(MACRO_PATH, dry_run=DRY_RUN, speed=speed)
        self.recorder = Recorder(MACRO_PATH)

    # ------------------------------------------------------------------ #
    def _build_ui(self):
        # ── Status ──────────────────────────────────────────────────────
        self.status_label = ctk.CTkLabel(self, text="Status: Idle",
                                         font=("Arial", 13, "bold"))
        self.status_label.pack(pady=(16, 4))

        self.info_label = ctk.CTkLabel(self, text="", font=("Arial", 11),
                                       text_color="gray")
        self.info_label.pack()

        # ── Controls ────────────────────────────────────────────────────
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=10)

        self.start_btn = ctk.CTkButton(btn_frame, text="▶ Start", width=90,
                                       command=self._on_start)
        self.start_btn.grid(row=0, column=0, padx=6)

        self.record_btn = ctk.CTkButton(btn_frame, text="⏺ Record", width=90,
                                        command=self._on_record)
        self.record_btn.grid(row=0, column=1, padx=6)

        self.stop_btn = ctk.CTkButton(btn_frame, text="■ Stop", width=90,
                                      fg_color="#c0392b", hover_color="#922b21",
                                      command=self._on_stop, state="disabled")
        self.stop_btn.grid(row=0, column=2, padx=6)

        # ── Options ─────────────────────────────────────────────────────
        opt_frame = ctk.CTkFrame(self, fg_color="transparent")
        opt_frame.pack(pady=6)

        # Macro file
        ctk.CTkLabel(opt_frame, text="Macro:", font=("Arial", 11)).grid(
            row=0, column=0, padx=6, sticky="e")
        self.macro_var = ctk.StringVar(value=MACRO_PATH)
        macro_entry = ctk.CTkEntry(opt_frame, textvariable=self.macro_var, width=140)
        macro_entry.grid(row=0, column=1, padx=4)
        ctk.CTkButton(opt_frame, text="📂", width=30,
                      command=self._browse_macro).grid(row=0, column=2, padx=2)

        # Loop count
        ctk.CTkLabel(opt_frame, text="Loops:", font=("Arial", 11)).grid(
            row=1, column=0, padx=6, sticky="e", pady=4)
        self.loop_var = ctk.IntVar(value=0)
        ctk.CTkEntry(opt_frame, textvariable=self.loop_var, width=60).grid(
            row=1, column=1, sticky="w", padx=4)
        ctk.CTkLabel(opt_frame, text="(0 = ∞)", font=("Arial", 10),
                     text_color="gray").grid(row=1, column=2, sticky="w")

        # Speed
        ctk.CTkLabel(opt_frame, text="Speed:", font=("Arial", 11)).grid(
            row=2, column=0, padx=6, sticky="e", pady=4)
        self.speed_var = ctk.DoubleVar(value=1.0)
        speed_slider = ctk.CTkSlider(opt_frame, from_=0.25, to=3.0,
                                     variable=self.speed_var, width=120,
                                     command=self._on_speed_change)
        speed_slider.grid(row=2, column=1, padx=4)
        self.speed_label = ctk.CTkLabel(opt_frame, text="1.00×",
                                        font=("Arial", 11))
        self.speed_label.grid(row=2, column=2, padx=4)

        # Log path
        self.log_label = ctk.CTkLabel(self, text=f"Log: {get_log_file()}",
                                      font=("Arial", 9), text_color="#555")
        self.log_label.pack(pady=(6, 0))

    # ------------------------------------------------------------------ #
    def _set_status(self, text, info=""):
        self.status_label.configure(text=f"Status: {text}")
        self.info_label.configure(text=info)

    def _on_speed_change(self, val):
        self.speed_label.configure(text=f"{float(val):.2f}×")

    def _browse_macro(self):
        from tkinter import filedialog
        path = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if path:
            self.macro_var.set(path)

    # ------------------------------------------------------------------ #
    def _on_start(self):
        if self._state != "idle":
            return
        self._state = "playing"
        self._toggle_buttons(playing=True)
        self._set_status("Starting...", "Focusing Heartopia...")
        self._new_player()

        def _start():
            if not DRY_RUN:
                ok = focus_game_window()
                if not ok:
                    self.after(0, lambda: self._set_status(
                        "Error", f"'{WINDOW_TITLE_KEYWORD}' window not found"))
                    self.after(0, self._reset_buttons)
                    self._state = "idle"
                    return
            self.after(0, lambda: self._set_status("Playing", "Running macro loop..."))
            logger.info("Playback started.")
            self.player.start()

        threading.Thread(target=_start, daemon=True).start()

    def _on_record(self):
        if self._state != "idle":
            return
        self._state = "recording"
        self._toggle_buttons(playing=True)
        self._set_status("Starting...", "Focusing Heartopia...")

        def _start():
            if not DRY_RUN:
                ok = focus_game_window()
                if not ok:
                    self.after(0, lambda: self._set_status(
                        "Error", f"'{WINDOW_TITLE_KEYWORD}' window not found"))
                    self.after(0, self._reset_buttons)
                    self._state = "idle"
                    return
            self.after(0, lambda: self._set_status("Recording", "Press ESC or Stop to finish"))
            logger.info("Recording started.")
            self.recorder.start()

        threading.Thread(target=_start, daemon=True).start()

    def _on_stop(self):
        if self._state == "playing":
            self.player.stop()
        elif self._state == "recording":
            self.recorder.stop()
            self.after(0, lambda: self._set_status("Idle", f"Saved → {self.macro_var.get()}"))
        self._state = "idle"
        self._reset_buttons()
        if self._state != "recording":
            self._set_status("Idle")

    def _toggle_buttons(self, playing):
        state_on = "normal" if not playing else "disabled"
        state_off = "disabled" if not playing else "normal"
        self.start_btn.configure(state=state_on)
        self.record_btn.configure(state=state_on)
        self.stop_btn.configure(state=state_off)

    def _reset_buttons(self):
        self._toggle_buttons(playing=False)


if __name__ == "__main__":
    app = App()
    app.mainloop()
