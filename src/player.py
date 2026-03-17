"""
player.py - Plays back recorded macro with human-like randomness.
"""
import time
import json
import random
import threading
import pydirectinput

pydirectinput.FAILSAFE = True
pydirectinput.PAUSE = 0.02

class Player:
    def __init__(self, macro_path="route_macro.json"):
        self.macro_path = macro_path
        self.actions = []
        self._running = False
        self._thread = None

    def load(self):
        with open(self.macro_path, 'r', encoding='utf-8') as f:
            self.actions = json.load(f)
        print(f"[Player] Loaded {len(self.actions)} actions from {self.macro_path}")

    def start(self):
        if self._running:
            return
        self.load()
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

    def _run_loop(self):
        """Loop through actions indefinitely until stopped."""
        while self._running:
            for action in self.actions:
                if not self._running:
                    break
                self._execute(action)
                # Small random pause between actions to feel human
                time.sleep(random.uniform(0.05, 0.2))

    def _execute(self, action):
        t = action.get("action")

        if t == "walk":
            key = action.get("key", "w")
            duration = action.get("duration", 1.0)
            # Add slight jitter to duration ±10%
            jitter = duration * random.uniform(-0.1, 0.1)
            actual = max(0.05, duration + jitter)
            pydirectinput.keyDown(key)
            time.sleep(actual)
            pydirectinput.keyUp(key)

        elif t == "interact":
            pydirectinput.keyDown('f')
            time.sleep(random.uniform(0.08, 0.18))
            pydirectinput.keyUp('f')

        elif t == "rotate":
            dx = action.get("dx", 0)
            dy = action.get("dy", 0)
            self._smooth_rotate(dx, dy)

    def _smooth_rotate(self, dx, dy):
        """Simulate right-click drag with smooth, human-like movement."""
        steps = max(5, (abs(dx) + abs(dy)) // 15)
        pydirectinput.mouseDown(button='right')
        time.sleep(random.uniform(0.03, 0.07))

        moved_x, moved_y = 0, 0
        for i in range(steps):
            # Distribute movement with slight curve (ease-in-out feel)
            t = (i + 1) / steps
            ease = t * t * (3 - 2 * t)  # smoothstep
            target_x = int(dx * ease)
            target_y = int(dy * ease)
            step_x = target_x - moved_x + random.randint(-1, 1)
            step_y = target_y - moved_y + random.randint(-1, 1)
            pydirectinput.moveRel(step_x, step_y, relative=True)
            moved_x += step_x
            moved_y += step_y
            time.sleep(random.uniform(0.008, 0.025))

        pydirectinput.mouseUp(button='right')
