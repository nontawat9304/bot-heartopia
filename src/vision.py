"""
vision.py - Screen capture, multi-scale template matching, and stuck detection.
"""
import time
import os
import cv2
import mss
import numpy as np

from src.logger import get_logger

logger = get_logger()

# Scales to try for multi-scale matching
_SCALES = [1.0, 0.85, 0.75, 1.15]


class Vision:
    def __init__(self, monitor_number=1, assets_dir="assets"):
        self.monitor_number = monitor_number
        with mss.mss() as sct:
            self.monitor = sct.monitors[monitor_number]
        self.assets_dir = assets_dir
        self.templates = {"resource": {}, "landmark": {}, "ui": {}}

        # Stuck detection state
        self._last_frame = None
        self._last_frame_time = 0.0
        self._consecutive_stuck = 0   # how many consecutive checks were "stuck"

        self.load_templates()

    # ------------------------------------------------------------------ #
    #  Template loading
    # ------------------------------------------------------------------ #
    def load_templates(self):
        if not os.path.exists(self.assets_dir):
            os.makedirs(self.assets_dir, exist_ok=True)
            return
        for filename in os.listdir(self.assets_dir):
            if not filename.endswith(".png"):
                continue
            filepath = os.path.join(self.assets_dir, filename)
            img = cv2.imread(filepath, cv2.IMREAD_COLOR)
            if img is None:
                logger.warning(f"Could not load template: {filepath}")
                continue
            category = "landmark"
            for prefix in ("resource", "landmark", "ui"):
                if filename.startswith(prefix):
                    category = prefix
                    break
            name = filename.rsplit(".", 1)[0]
            self.templates[category][name] = img
            logger.debug(f"Template loaded: [{category}] {name} {img.shape}")

    # ------------------------------------------------------------------ #
    #  Screen capture
    # ------------------------------------------------------------------ #
    def capture_screen(self, region=None):
        """Capture full screen or sub-region {top, left, width, height}. Returns BGR."""
        with mss.mss() as sct:
            target = region if region else self.monitor
            sct_img = sct.grab(target)
        img = np.array(sct_img)
        return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

    def capture_region_ratio(self, x=0.0, y=0.0, w=1.0, h=1.0):
        """
        Capture a sub-region defined as ratio of screen size.
        e.g. x=0.3, y=0.3, w=0.4, h=0.4 = center 40% of screen.
        """
        mw = self.monitor["width"]
        mh = self.monitor["height"]
        region = {
            "left":   self.monitor["left"] + int(mw * x),
            "top":    self.monitor["top"]  + int(mh * y),
            "width":  int(mw * w),
            "height": int(mh * h),
        }
        return self.capture_screen(region)

    # ------------------------------------------------------------------ #
    #  Template matching (multi-scale + grayscale + confidence)
    # ------------------------------------------------------------------ #
    def detect_template(self, screen, template, threshold=0.78, grayscale=True,
                        multi_scale=True):
        """
        Returns (cx, cy, confidence) of best match or None.
        Tries multiple scales to handle resolution differences.
        """
        s_gray = cv2.cvtColor(screen, cv2.COLOR_BGR2GRAY) if grayscale else screen
        t_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY) if grayscale else template

        best_val = -1.0
        best_loc = None
        best_size = template.shape[:2]

        scales = _SCALES if multi_scale else [1.0]
        for scale in scales:
            if scale != 1.0:
                th, tw = t_gray.shape[:2]
                new_w = max(1, int(tw * scale))
                new_h = max(1, int(th * scale))
                # Skip if template larger than screen
                if new_h >= s_gray.shape[0] or new_w >= s_gray.shape[1]:
                    continue
                t_scaled = cv2.resize(t_gray, (new_w, new_h))
            else:
                t_scaled = t_gray
                new_h, new_w = t_gray.shape[:2]

            if t_scaled.shape[0] > s_gray.shape[0] or t_scaled.shape[1] > s_gray.shape[1]:
                continue

            result = cv2.matchTemplate(s_gray, t_scaled, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(result)
            if max_val > best_val:
                best_val = max_val
                best_loc = max_loc
                best_size = (new_h, new_w)

        if best_val >= threshold and best_loc is not None:
            cx = best_loc[0] + best_size[1] // 2
            cy = best_loc[1] + best_size[0] // 2
            return (cx, cy, best_val)
        return None

    def find_any_target(self, screen, category="resource", threshold=0.78):
        """Returns (name, (cx, cy), confidence) for best match in category, or None."""
        best = None
        for name, tmpl in self.templates[category].items():
            match = self.detect_template(screen, tmpl, threshold)
            if match and (best is None or match[2] > best[2]):
                best = (name, (match[0], match[1]), match[2])
        if best:
            logger.debug(f"Found [{category}] {best[0]} conf={best[2]:.3f} at {best[1]}")
        return best

    def see_object(self, label, screen=None, threshold=0.78,
                   confirm_frames=1, region=None):
        """
        Check if a named object is visible. label = 'category:name'.
        confirm_frames: require N consecutive detections to avoid false positives.
        Returns True/False.
        """
        if screen is None:
            screen = self.capture_screen(region)

        if ":" in label:
            category, name = label.split(":", 1)
        else:
            category, name = "landmark", label

        tmpl = self.templates.get(category, {}).get(name)
        if tmpl is None:
            logger.warning(f"Template not found: {label}")
            return False

        hits = 0
        for _ in range(confirm_frames):
            if confirm_frames > 1:
                screen = self.capture_screen(region)
            match = self.detect_template(screen, tmpl, threshold)
            if match:
                hits += 1
            else:
                break

        found = hits >= confirm_frames
        if found:
            logger.debug(f"see_object confirmed: {label} (conf_frames={confirm_frames})")
        return found

    # ------------------------------------------------------------------ #
    #  Stuck detection  (movement-aware)
    # ------------------------------------------------------------------ #
    def is_stuck(self, threshold=0.993, min_interval=0.5,
                 moving=True, required_consecutive=2):
        """
        Returns True only when:
          - moving=True (caller signals movement intent)
          - frame similarity >= threshold for `required_consecutive` checks in a row

        This prevents false positives during loading screens / cutscenes.
        """
        if not moving:
            self._consecutive_stuck = 0
            return False

        now = time.time()
        if now - self._last_frame_time < min_interval:
            return False

        # Crop center 60% of screen (avoids static HUD edges)
        mw = self.monitor["width"]
        mh = self.monitor["height"]
        region = {
            "left":   self.monitor["left"] + int(mw * 0.2),
            "top":    self.monitor["top"]  + int(mh * 0.2),
            "width":  int(mw * 0.6),
            "height": int(mh * 0.6),
        }
        frame = self.capture_screen(region)
        small = cv2.resize(frame, (256, 144))
        gray  = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)

        stuck = False
        if self._last_frame is not None:
            diff  = cv2.absdiff(gray, self._last_frame)
            score = 1.0 - (diff.mean() / 255.0)
            if score >= threshold:
                self._consecutive_stuck += 1
            else:
                self._consecutive_stuck = 0
            stuck = self._consecutive_stuck >= required_consecutive
            logger.debug(f"Frame sim={score:.4f} consec={self._consecutive_stuck} stuck={stuck}")

        self._last_frame = gray
        self._last_frame_time = now
        return stuck

    def reset_stuck_counter(self):
        self._consecutive_stuck = 0
        self._last_frame = None
