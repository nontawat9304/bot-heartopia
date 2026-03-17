"""
recorder.py - Records keyboard (wasd, f) and mouse right-drag (camera rotate) actions.
Saves to a JSON file for later playback.
"""
import time
import json
import threading
import random
from pynput import keyboard, mouse

RECORD_KEYS = {'w', 'a', 's', 'd', 'f'}

class Recorder:
    def __init__(self, output_path="route_macro.json"):
        self.output_path = output_path
        self.actions = []
        self._recording = False
        self._key_states = {}       # key -> press time
        self._rmb_down = False
        self._rmb_start_pos = None
        self._rmb_start_time = None
        self._kb_listener = None
        self._ms_listener = None

    def start(self):
        self._recording = True
        self.actions = []
        self._key_states = {}
        print("[Recorder] Recording started. Press ESC to stop.")

        self._kb_listener = keyboard.Listener(
            on_press=self._on_key_press,
            on_release=self._on_key_release
        )
        self._ms_listener = mouse.Listener(
            on_click=self._on_click,
            on_move=self._on_move
        )
        self._kb_listener.start()
        self._ms_listener.start()

    def stop(self):
        self._recording = False
        if self._kb_listener:
            self._kb_listener.stop()
        if self._ms_listener:
            self._ms_listener.stop()
        self._save()
        print(f"[Recorder] Saved {len(self.actions)} actions to {self.output_path}")

    def _on_key_press(self, key):
        if not self._recording:
            return
        try:
            k = key.char.lower() if hasattr(key, 'char') and key.char else None
        except Exception:
            k = None

        if k in RECORD_KEYS and k not in self._key_states:
            self._key_states[k] = time.time()

        # ESC stops recording
        if key == keyboard.Key.esc:
            threading.Thread(target=self.stop, daemon=True).start()

    def _on_key_release(self, key):
        if not self._recording:
            return
        try:
            k = key.char.lower() if hasattr(key, 'char') and key.char else None
        except Exception:
            k = None

        if k in RECORD_KEYS and k in self._key_states:
            duration = time.time() - self._key_states.pop(k)
            duration = round(duration, 3)
            if k == 'f':
                self.actions.append({"action": "interact"})
            else:
                self.actions.append({"action": "walk", "key": k, "duration": duration})

    def _on_click(self, x, y, button, pressed):
        if not self._recording:
            return
        if button == mouse.Button.right:
            if pressed:
                self._rmb_down = True
                self._rmb_start_pos = (x, y)
                self._rmb_start_time = time.time()
            else:
                if self._rmb_down and self._rmb_start_pos:
                    dx = x - self._rmb_start_pos[0]
                    dy = y - self._rmb_start_pos[1]
                    self.actions.append({"action": "rotate", "dx": dx, "dy": dy})
                self._rmb_down = False
                self._rmb_start_pos = None

    def _on_move(self, x, y):
        # We only care about final position on release, handled in _on_click
        pass

    def _save(self):
        with open(self.output_path, 'w', encoding='utf-8') as f:
            json.dump(self.actions, f, indent=4, ensure_ascii=False)
