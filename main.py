"""
main.py - GUI for Heartopia macro bot.
Start: focuses Heartopia window then plays macro.
Record: records new macro and saves to route_macro.json.
Stop: stops playback or recording.
"""
import threading
import time
import customtkinter as ctk
import pygetwindow as gw

from src.player import Player
from src.recorder import Recorder
from src.logger import get_logger

MACRO_PATH = "route_macro.json"
WINDOW_TITLE_KEYWORD = "Heartopia"

logger = get_logger()

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


def focus_game_window():
    """Find and focus the Heartopia window."""
    wins = [w for w in gw.getAllWindows() if WINDOW_TITLE_KEYWORD.lower() in w.title.lower()]
    if not wins:
        logger.warning(f"Window '{WINDOW_TITLE_KEYWORD}' not found.")
        return False
    win = wins[0]
    try:
        win.activate()
        time.sleep(0.5)
        logger.info(f"Focused window: {win.title}")
        return True
    except Exception as e:
        logger.error(f"Could not focus window: {e}")
        return False


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Heartopia Bot")
        self.geometry("300x200")
        self.resizable(False, False)

        self.player = Player(MACRO_PATH)
        self.recorder = Recorder(MACRO_PATH)
        self._state = "idle"  # idle | playing | recording

        self._build_ui()

    def _build_ui(self):
        self.status_label = ctk.CTkLabel(self, text="Status: Idle", font=("Arial", 13))
        self.status_label.pack(pady=(20, 10))

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=5)

        self.start_btn = ctk.CTkButton(btn_frame, text="▶ Start", width=80, command=self._on_start)
        self.start_btn.grid(row=0, column=0, padx=8)

        self.record_btn = ctk.CTkButton(btn_frame, text="⏺ Record", width=80, command=self._on_record)
        self.record_btn.grid(row=0, column=1, padx=8)

        self.stop_btn = ctk.CTkButton(btn_frame, text="■ Stop", width=80,
                                      fg_color="#c0392b", hover_color="#922b21",
                                      command=self._on_stop, state="disabled")
        self.stop_btn.grid(row=0, column=2, padx=8)

        self.info_label = ctk.CTkLabel(self, text="", font=("Arial", 11), text_color="gray")
        self.info_label.pack(pady=(10, 0))

    def _set_status(self, text, info=""):
        self.status_label.configure(text=f"Status: {text}")
        self.info_label.configure(text=info)

    def _on_start(self):
        if self._state != "idle":
            return
        self._state = "playing"
        self.start_btn.configure(state="disabled")
        self.record_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self._set_status("Starting...", "Focusing Heartopia...")

        def _start():
            ok = focus_game_window()
            if not ok:
                self.after(0, lambda: self._set_status("Error", f"'{WINDOW_TITLE_KEYWORD}' window not found"))
                self.after(0, self._reset_buttons)
                self._state = "idle"
                return
            logger.info("Starting playback.")
            self.after(0, lambda: self._set_status("Playing", "Running macro loop..."))
            self.player.start()

        threading.Thread(target=_start, daemon=True).start()

    def _on_record(self):
        if self._state != "idle":
            return
        self._state = "recording"
        self.start_btn.configure(state="disabled")
        self.record_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self._set_status("Recording", "Press ESC or Stop to finish")
        logger.info("Starting recording.")
        self.recorder.start()

    def _on_stop(self):
        if self._state == "playing":
            self.player.stop()
            logger.info("Playback stopped.")
        elif self._state == "recording":
            self.recorder.stop()
            logger.info("Recording stopped and saved.")
            self.after(0, lambda: self._set_status("Idle", f"Saved to {MACRO_PATH}"))
        self._state = "idle"
        self._reset_buttons()
        if self._state != "recording":
            self._set_status("Idle")

    def _reset_buttons(self):
        self.start_btn.configure(state="normal")
        self.record_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")


if __name__ == "__main__":
    app = App()
    app.mainloop()
