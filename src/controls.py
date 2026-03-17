import time
import random
import pydirectinput

pydirectinput.FAILSAFE = True
pydirectinput.PAUSE = 0.05

class Controls:
    def sleep_random(self, mn=0.5, mx=1.5):
        time.sleep(random.uniform(mn, mx))

    def hold_key(self, key):
        pydirectinput.keyDown(key)

    def release_key(self, key):
        pydirectinput.keyUp(key)

    def press_key(self, key):
        pydirectinput.keyDown(key)
        time.sleep(random.uniform(0.05, 0.15))
        pydirectinput.keyUp(key)

    def walk_forward(self, duration=1.0):
        self.hold_key('w')
        time.sleep(duration + random.uniform(-0.05, 0.05))
        self.release_key('w')

    def stop_walking(self):
        for k in ('w','a','s','d'):
            pydirectinput.keyUp(k)

    def jump(self):
        self.press_key('space')

    def interact(self):
        self.press_key('f')

    def rotate_camera(self, x_offset=0, y_offset=0, steps=10):
        pydirectinput.mouseDown(button='right')
        time.sleep(0.05)
        sx = int(x_offset / steps)
        sy = int(y_offset / steps)
        for _ in range(steps):
            pydirectinput.moveRel(sx + random.randint(-2,2), sy + random.randint(-1,1), relative=True)
            time.sleep(random.uniform(0.01, 0.03))
        pydirectinput.mouseUp(button='right')

    def rotate_camera_angle(self, degrees):
        pixels_per_degree = 5
        actual = degrees + random.uniform(-5.0, 5.0)
        x_offset = int(actual * pixels_per_degree)
        self.rotate_camera(x_offset=x_offset, steps=max(5, abs(x_offset)//20))

    def rotate_camera_random(self):
        self.rotate_camera_angle(random.choice([-90, -45, 45, 90, 180]))