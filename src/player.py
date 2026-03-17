"""
player.py - Plays back macro with state-based conditions, humanization, and anti-stuck.

Supported action types:
  walk      { "action": "walk", "key": "w", "duration": 2.0,
               "until": "resource:resource_bery", "tag": "search_phase" }
  rotate    { "action": "rotate", "dx": 100, "dy": 0 }
  interact  { "action": "interact" }
  wait      { "action": "wait", "min": 0.5, "max": 1.2 }
  loop      { "loop": 3, "actions": [...] }   (-1 = infinite)
"""
import time
import json
import random
import threading
import pydirectinput

from src.logger import get_logger
from src.vision import Vision
from src.anti_stuck import AntiStuck
from src.macro_validator import validate_and_log

pydirectinput.FAILSAFE = True
pydirectinput.PAUSE = 0.02

logger = get_logger()

# Direction offset keys for imperfect path simulation
_STRAFE_KEYS = ("a", "d")


class Player:
    def __init__(self, macro_path="route_macro.json", dry_run=False, speed=1.0):
        self.macro_path = macro_path
        self.dry_run = dry_run
        self.speed = max(0.1, speed)
        self.actions = []
        self._running = False
        self._thread = None
        self.vision = Vision()
        self.anti_stuck = AntiStuck(self.vision)

    # ------------------------------------------------------------------ #
    #  Public API
    # ------------------------------------------------------------------ #
    def load(self):
        with open(self.macro_path, "r", encoding="utf-8") as f:
            self.actions = json.load(f)
        logger.info(f"Loaded {len(self.actions)} top-level actions from {self.macro_path}")
        if not validate_and_log(self.actions):
            logger.warning("Macro has validation errors — proceeding anyway, check logs.")

    def start(self):
        if self._running:
            return
        self.load()
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        self.anti_stuck.set_moving(False)
        logger.info("Player stopped.")

    # ------------------------------------------------------------------ #
    #  Main loop
    # ------------------------------------------------------------------ #
    def _run_loop(self):
        logger.info("Playback loop started.")
        while self._running:
            self._execute_list(self.actions)
            idle = random.uniform(0.5, 2.0)
            logger.debug(f"Loop idle: {idle:.2f}s")
            self._sleep(idle)

    def _execute_list(self, actions):
        for action in actions:
            if not self._running:
                return
            self.anti_stuck.check()
            self._execute(action)
            self._sleep(random.uniform(0.04, 0.18))

    def _execute(self, action):
        # ── loop block ──────────────────────────────────────────────────
        if "loop" in action:
            count = action["loop"]
            sub   = action.get("actions", [])
            tag   = action.get("tag", "")
            i = 0
            while self._running and (count < 0 or i < count):
                logger.debug(f"Loop [{tag}] iter {i + 1}")
                self._execute_list(sub)
                i += 1
            return

        t   = action.get("action")
        tag = action.get("tag", "")
        pfx = f"[{tag}] " if tag else ""

        # ── walk ─────────────────────────────────────────────────────────
        if t == "walk":
            self._do_walk(action, pfx)

        # ── rotate ───────────────────────────────────────────────────────
        elif t == "rotate":
            dx = action.get("dx", 0)
            dy = action.get("dy", 0)
            logger.info(f"{pfx}Rotate dx={dx} dy={dy}")
            if not self.dry_run:
                self._smooth_rotate(dx, dy)

        # ── interact ─────────────────────────────────────────────────────
        elif t == "interact":
            logger.info(f"{pfx}Interact (F)")
            if not self.dry_run:
                pydirectinput.keyDown("f")
                time.sleep(random.uniform(0.08, 0.18))
                pydirectinput.keyUp("f")

        # ── wait ─────────────────────────────────────────────────────────
        elif t == "wait":
            mn  = action.get("min", 0.5) / self.speed
            mx  = action.get("max", 1.5) / self.speed
            dur = random.uniform(mn, mx)
            logger.info(f"{pfx}Wait {dur:.2f}s")
            self._sleep(dur)

        else:
            logger.warning(f"Unknown action type: '{t}'")

    # ------------------------------------------------------------------ #
    #  Walk — humanized + movement-aware anti-stuck
    # ------------------------------------------------------------------ #
    def _do_walk(self, action, pfx):
        key      = action.get("key", "w")
        duration = action.get("duration", 1.0) / self.speed
        until    = action.get("until")
        jitter   = duration * random.uniform(-0.08, 0.08)
        actual   = max(0.05, duration + jitter)

        stop_reason = "timeout"
        logger.info(f"{pfx}Walk '{key}' {actual:.2f}s" +
                    (f" until={until}" if until else ""))

        if self.dry_run:
            return

        self.anti_stuck.set_moving(True)
        pydirectinput.keyDown(key)
        t_start = time.time()
        elapsed = 0.0
        step    = 0.1
        _next_strafe = time.time() + random.uniform(0.8, 2.0)  # imperfect path timer

        while elapsed < actual and self._running:
            time.sleep(step)
            elapsed = time.time() - t_start

            # Micro mouse jitter (subtle, low frequency)
            if random.random() < 0.10:
                pydirectinput.moveRel(
                    random.randint(-1, 1), random.randint(-1, 1), relative=True
                )

            # Imperfect path: occasional brief strafe
            now = time.time()
            if now >= _next_strafe:
                strafe_key = random.choice(_STRAFE_KEYS)
                strafe_dur = random.uniform(0.04, 0.10)
                pydirectinput.keyDown(strafe_key)
                time.sleep(strafe_dur)
                pydirectinput.keyUp(strafe_key)
                _next_strafe = now + random.uniform(1.0, 3.0)

            # Vision condition check (with fallback: require 2 confirms)
            if until and self.vision.see_object(until, confirm_frames=2):
                stop_reason = f"until:{until}"
                break

        pydirectinput.keyUp(key)
        self.anti_stuck.set_moving(False)

        actual_elapsed = time.time() - t_start
        logger.info(f"{pfx}Walk done — {actual_elapsed:.2f}s, reason={stop_reason}")

    # ------------------------------------------------------------------ #
    #  Helpers
    # ------------------------------------------------------------------ #
    def _sleep(self, seconds):
        end = time.time() + seconds
        while time.time() < end and self._running:
            time.sleep(0.05)

    def _smooth_rotate(self, dx, dy):
        steps = max(5, (abs(dx) + abs(dy)) // 15)
        pydirectinput.mouseDown(button="right")
        time.sleep(random.uniform(0.03, 0.07))
        mx = my = 0
        for i in range(steps):
            t    = (i + 1) / steps
            ease = t * t * (3 - 2 * t)
            tx   = int(dx * ease)
            ty   = int(dy * ease)
            sx   = tx - mx + random.randint(-1, 1)
            sy   = ty - my + random.randint(-1, 1)
            pydirectinput.moveRel(sx, sy, relative=True)
            mx  += sx
            my  += sy
            time.sleep(random.uniform(0.008, 0.025))
        pydirectinput.mouseUp(button="right")
