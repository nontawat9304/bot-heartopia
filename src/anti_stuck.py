"""
anti_stuck.py - Movement-aware stuck detection and varied recovery chains.
"""
import time
import random
import pydirectinput

from src.logger import get_logger

logger = get_logger()

STUCK_TIMEOUT    = 3.0   # seconds before triggering recovery
CHECK_INTERVAL   = 0.5   # vision check throttle

# Recovery chains: list of (action, params) tuples
# actions: "turn", "jump", "walk", "strafe", "backstep"
_RECOVERY_CHAINS = [
    # chain 1: backstep → random turn → forward
    [("backstep", 0.6), ("turn", None), ("walk", 0.5)],
    # chain 2: jump → turn → jump again
    [("jump", None), ("turn", None), ("jump", None), ("walk", 0.4)],
    # chain 3: strafe left/right → turn
    [("strafe", "a"), ("strafe", "d"), ("turn", None)],
    # chain 4: big turn + forward
    [("turn_big", None), ("walk", 0.8)],
    # chain 5: backstep + strafe + jump
    [("backstep", 0.4), ("strafe", "a"), ("jump", None), ("walk", 0.6)],
]


class AntiStuck:
    def __init__(self, vision):
        self.vision = vision
        self._stuck_since = None
        self._moving = False          # set by player to signal movement intent
        self._last_chain_idx = -1     # avoid repeating same chain twice in a row

    def set_moving(self, moving: bool):
        """Player calls this to tell anti-stuck whether movement is expected."""
        self._moving = moving
        if not moving:
            self.vision.reset_stuck_counter()

    def check(self):
        """
        Call in main loop. Returns True if recovery was triggered.
        Only active when movement is expected (_moving=True).
        """
        if not self.vision.is_stuck(
            threshold=0.993,
            min_interval=CHECK_INTERVAL,
            moving=self._moving,
            required_consecutive=2,
        ):
            self._stuck_since = None
            return False

        now = time.time()
        if self._stuck_since is None:
            self._stuck_since = now
            return False

        elapsed = now - self._stuck_since
        if elapsed >= STUCK_TIMEOUT:
            logger.warning(f"Stuck confirmed ({elapsed:.1f}s) — recovering")
            self._recover()
            self._stuck_since = None
            self.vision.reset_stuck_counter()
            return True

        return False

    # ------------------------------------------------------------------ #
    def _recover(self):
        # Pick a chain different from last one
        available = [i for i in range(len(_RECOVERY_CHAINS)) if i != self._last_chain_idx]
        idx = random.choice(available)
        self._last_chain_idx = idx
        chain = _RECOVERY_CHAINS[idx]
        logger.info(f"Recovery chain #{idx}: {[s[0] for s in chain]}")

        for step, param in chain:
            if step == "turn":
                self._random_turn(small=True)
            elif step == "turn_big":
                self._random_turn(small=False)
            elif step == "jump":
                self._jump()
            elif step == "walk":
                dur = param if isinstance(param, float) else random.uniform(0.3, 0.7)
                self._walk("w", dur)
            elif step == "backstep":
                dur = param if isinstance(param, float) else random.uniform(0.3, 0.6)
                self._walk("s", dur)
            elif step == "strafe":
                key = param if param in ("a", "d") else random.choice(("a", "d"))
                self._walk(key, random.uniform(0.3, 0.6))
            time.sleep(random.uniform(0.05, 0.15))

    # ------------------------------------------------------------------ #
    def _random_turn(self, small=True):
        if small:
            angle = random.choice([-60, -45, 45, 60, 90])
        else:
            angle = random.choice([-135, -180, 135, 180])
        # Add noise ±15°
        angle += random.uniform(-15, 15)
        pixels = int(angle * 5)
        steps = max(5, abs(pixels) // 20)
        pydirectinput.mouseDown(button="right")
        time.sleep(random.uniform(0.03, 0.06))
        moved = 0
        for i in range(steps):
            t = (i + 1) / steps
            ease = t * t * (3 - 2 * t)
            target = int(pixels * ease)
            step = target - moved + random.randint(-2, 2)
            pydirectinput.moveRel(step, random.randint(-2, 2), relative=True)
            moved += step
            time.sleep(random.uniform(0.008, 0.022))
        pydirectinput.mouseUp(button="right")
        logger.debug(f"Turn: {angle:.0f}° ({pixels}px)")

    def _jump(self):
        pydirectinput.keyDown("space")
        time.sleep(random.uniform(0.08, 0.16))
        pydirectinput.keyUp("space")

    def _walk(self, key, duration):
        pydirectinput.keyDown(key)
        time.sleep(max(0.1, duration + random.uniform(-0.05, 0.05)))
        pydirectinput.keyUp(key)
