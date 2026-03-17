# Heartopia Bot — คู่มือใช้งาน

## ความต้องการของระบบ
- Python 3.10+
- Windows (ใช้ pydirectinput ซึ่ง Windows only)
- เกม Heartopia เปิดอยู่ก่อนกด Start

---

## การติดตั้งและรัน

ดับเบิลคลิก `run.bat` — จะติดตั้ง dependencies อัตโนมัติแล้วเปิด GUI

หรือรันด้วย command line:
```bash
cd bot-heartopia
pip install -r requirements.txt
python main.py
```

ทดสอบโดยไม่กด key จริง (dry-run):
```bash
python main.py --dry-run
```

---

## หน้าต่าง GUI

```
┌─────────────────────────────────────┐
│  Status: Idle                        │
│                                      │
│  [ ▶ Start ] [ ⏺ Record ] [ ■ Stop ] │
│                                      │
│  Macro: route_macro.json  [📂]       │
│  Loops: 0  (0 = ∞)                  │
│  Speed: ──●────  1.00×              │
│                                      │
│  Log: logs/session_YYYYMMDD.log     │
└─────────────────────────────────────┘
```

| ปุ่ม | ทำอะไร |
|------|--------|
| ▶ Start | โหลด macro → focus เกม → เล่นวนลูป |
| ⏺ Record | บันทึก input ของคุณ → บันทึกเป็น JSON |
| ■ Stop | หยุด playback หรือ recording |

**ตัวเลือก:**
- `Macro` — เลือกไฟล์ JSON ที่จะใช้ (กด 📂 เพื่อ browse)
- `Loops` — จำนวนรอบที่จะเล่น (0 = วนไม่หยุด)
- `Speed` — ความเร็ว 0.25× ถึง 3× (กระทบ duration ของ walk/wait)

---

## การ Record Macro ใหม่

1. กด **⏺ Record**
2. เล่นเกมตามปกติ — bot จะจับ:
   - เดิน `W A S D`
   - กด interact `F`
   - หมุนกล้อง (right-click drag)
3. กด **■ Stop** หรือ `ESC` เพื่อหยุดและบันทึก
4. ไฟล์จะถูกบันทึกที่ `route_macro.json` (หรือไฟล์ที่เลือกไว้)

---

## รูปแบบ Macro JSON

### action พื้นฐาน

```json
{ "action": "walk", "key": "w", "duration": 2.5, "tag": "move_forward" }
{ "action": "rotate", "dx": 150, "dy": -30 }
{ "action": "interact" }
{ "action": "wait", "min": 0.5, "max": 1.2 }
```

### walk หยุดเมื่อเจอ object (vision condition)

```json
{
  "action": "walk",
  "key": "w",
  "duration": 5.0,
  "until": "resource:resource_bery",
  "tag": "search_phase"
}
```
bot จะเดินสูงสุด 5 วิ แต่ถ้าเจอ `resource_bery` บนหน้าจอก่อน จะหยุดทันที

### loop block

```json
{
  "loop": 3,
  "tag": "patrol",
  "actions": [
    { "action": "walk", "key": "w", "duration": 2.0 },
    { "action": "rotate", "dx": 90, "dy": 0 }
  ]
}
```
ใช้ `"loop": -1` สำหรับวนไม่หยุด

### ตัวอย่าง macro เต็ม

```json
[
  { "action": "wait", "min": 0.5, "max": 1.0, "tag": "startup" },
  {
    "loop": -1,
    "tag": "main_loop",
    "actions": [
      { "action": "walk", "key": "w", "duration": 3.0, "until": "resource:resource_bery" },
      { "action": "interact", "tag": "collect" },
      { "action": "wait", "min": 0.8, "max": 1.5 },
      { "action": "rotate", "dx": 180, "dy": 0 },
      { "action": "walk", "key": "w", "duration": 2.0 }
    ]
  }
]
```

---

## Vision / Template Matching

ใช้สำหรับ `until` condition ใน walk action

**วิธีเพิ่ม template:**
1. จับภาพ object ที่ต้องการ detect (crop เฉพาะส่วน ไม่ต้องทั้งจอ)
2. บันทึกเป็น `.png` ใส่ในโฟลเดอร์ `assets/`
3. ตั้งชื่อตาม prefix:

| prefix | หมวด | ตัวอย่าง |
|--------|------|---------|
| `resource_` | ของที่เก็บได้ | `resource_bery.png` |
| `landmark_` | จุดสังเกต | `landmark_tree.png` |
| `ui_` | UI ในเกม | `ui_quest_icon.png` |

**ใช้ใน macro:**
```json
"until": "resource:resource_bery"
          ^^^^^^^^  ^^^^^^^^^^^^^
          หมวด      ชื่อไฟล์ (ไม่มี .png)
```

---

## Anti-Stuck System

ทำงานอัตโนมัติ ไม่ต้องตั้งค่า

- เช็ค frame ทุก 0.5 วิ **เฉพาะตอนที่ bot กำลังเดิน**
- ถ้าภาพไม่เปลี่ยน 2 ครั้งติด (≥ 1 วิ) → เริ่มนับ
- ถ้า stuck นาน > 3 วิ → trigger recovery อัตโนมัติ

Recovery มี 5 รูปแบบ สุ่มและไม่ซ้ำกัน 2 ครั้งติด:
- backstep → turn → walk
- jump → turn → jump → walk
- strafe ซ้าย/ขวา → turn
- big turn → walk
- backstep → strafe → jump → walk

---

## Log Files

ทุก session บันทึกที่ `logs/session_YYYYMMDD_HHMMSS.log`

```
10:23:01 [INFO]  Loaded 2 top-level actions
10:23:01 [INFO]  Macro validation passed.
10:23:02 [INFO]  [search_phase] Walk 'w' 2.48s until=resource:resource_bery
10:23:04 [INFO]  Condition met: resource:resource_bery — stopping walk early
10:23:04 [INFO]  [search_phase] Walk done — 2.01s, reason=until:resource:resource_bery
10:23:05 [WARNING] Stuck confirmed (3.1s) — recovering
10:23:05 [INFO]  Recovery chain #2: ['strafe', 'strafe', 'turn']
```

---

## Macro Validation

ทุกครั้งที่กด Start bot จะตรวจ JSON ก่อนรัน ถ้ามี error จะ log warning แต่ยังรันต่อได้

สิ่งที่ตรวจ:
- `action` ต้องเป็น walk / rotate / interact / wait
- `key` ของ walk ต้องเป็น w/a/s/d
- `duration` ต้องมากกว่า 0
- `wait` ต้องมี min ≤ max
- `loop` ต้องมี `actions` เป็น list

---

## โครงสร้างไฟล์

```
bot-heartopia/
├── main.py              # GUI หลัก
├── run.bat              # รันได้เลย (ติดตั้ง deps อัตโนมัติ)
├── route_macro.json     # macro ที่ใช้งาน
├── requirements.txt
├── assets/              # template images สำหรับ vision
│   └── resource_bery.png
├── logs/                # session logs (สร้างอัตโนมัติ)
└── src/
    ├── player.py        # เล่น macro
    ├── recorder.py      # บันทึก macro
    ├── vision.py        # template matching + stuck detection
    ├── anti_stuck.py    # recovery system
    ├── macro_validator.py
    ├── controls.py
    └── logger.py
```
