import time
import os
import cv2
import mss
import numpy as np

class Vision:
    def __init__(self, monitor_number=1, assets_dir="assets"):
        """
        Initializes the vision module.
        monitor_number: 1 is the primary monitor. 
        """
        self.monitor_number = monitor_number
        with mss.mss() as sct:
            self.monitor = sct.monitors[monitor_number]
        self.assets_dir = assets_dir
        
        # Load templates mapping: { "category": { "name": image_data } }
        self.templates = {
            "resource": {},
            "landmark": {}
        }
        self.load_templates()
        
    def load_templates(self):
        """Loads all .png files from assets/ into memory for fast matching."""
        if not os.path.exists(self.assets_dir):
            print(f"Directory {self.assets_dir} not found. Creating it.")
            os.makedirs(self.assets_dir, exist_ok=True)
            return

        for filename in os.listdir(self.assets_dir):
            if filename.endswith(".png"):
                filepath = os.path.join(self.assets_dir, filename)
                img = cv2.imread(filepath, cv2.IMREAD_COLOR)
                if img is None:
                    print(f"Warning: Could not load {filepath}")
                    continue
                
                # Determine category by prefix (e.g., "resource_tree.png", "landmark_rock.png")
                category = "landmark" # default
                if filename.startswith("resource"):
                    category = "resource"
                elif filename.startswith("landmark"):
                    category = "landmark"
                    
                name = filename.split('.')[0]
                self.templates[category][name] = img
                print(f"Loaded template: {category} -> {name} (Shape: {img.shape})")

    def capture_screen(self):
        """Captures the screen and returns it as an OpenCV image (BGR)."""
        with mss.mss() as sct:
            sct_img = sct.grab(self.monitor)
            
        # Convert mss image (BGRA) to OpenCV format (BGR)
        img = np.array(sct_img)
        img_bgr = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        return img_bgr

    def detect_template(self, screen_image, template, threshold=0.7):
        """
        Detects a template in the screen image using cv2.matchTemplate.
        Returns a tuple of (center_x, center_y) if found, else None.
        """
        result = cv2.matchTemplate(screen_image, template, cv2.TM_CCOEFF_NORMED)
        loc = np.where(result >= threshold)
        
        if len(loc[0]) > 0:
            # We found at least one match!
            # Let's take the first one (or the best one)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            
            # max_loc is the top-left corner of the best match
            top_left = max_loc
            h, w = template.shape[:2]
            
            # Calculate center
            center_x = top_left[0] + w // 2
            center_y = top_left[1] + h // 2
            
            return (center_x, center_y)
            
        return None

    def find_any_target(self, screen_image, category="resource", threshold=0.7):
        """
        Searches the screen for ANY template in the given category.
        Returns: (target_name, (center_x, center_y)) or None
        """
        for name, template in self.templates[category].items():
            result = self.detect_template(screen_image, template, threshold)
            if result:
                return (name, result)
        return None

if __name__ == "__main__":
    v = Vision()
    print("Templates loaded:", v.templates)
