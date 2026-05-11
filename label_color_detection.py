"""
PET Bottle Label Color Detection - YOLO + HSV
For ETRobocon / Google Colab

Setup (run in the first Colab cell):
  !pip install ultralytics opencv-python-headless matplotlib
"""

# ========================
# 1. Imports
# ========================
import cv2
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches

from ultralytics import YOLO
from google.colab import files


# ========================
# 2. Color definitions (HSV color space)
# ========================
# HSV: Hue(0-179), Saturation(0-255), Value(0-255)

COLOR_RANGES = {
    "Red": [
        (np.array([0,   100, 80]),  np.array([10,  255, 255])),
        (np.array([165, 100, 80]),  np.array([179, 255, 255])),
    ],
    "Orange":     [(np.array([11,  100, 80]),  np.array([25,  255, 255]))],
    "Yellow":     [(np.array([26,  100, 80]),  np.array([35,  255, 255]))],
    "YellowGreen":[(np.array([36,  80,  80]),  np.array([65,  255, 255]))],
    "Green":      [(np.array([66,  80,  80]),  np.array([95,  255, 255]))],
    "Cyan":       [(np.array([96,  80,  80]),  np.array([110, 255, 255]))],
    "Blue":       [(np.array([111, 80,  60]),  np.array([130, 255, 255]))],
    "Purple":     [(np.array([131, 60,  60]),  np.array([155, 255, 255]))],
    "Pink":       [(np.array([156, 60,  80]),  np.array([164, 255, 255]))],
    "White":      [(np.array([0,   0,   180]), np.array([179, 40,  255]))],
    "Black":      [(np.array([0,   0,   0]),   np.array([179, 255, 60]))],
}

COLOR_RGB = {
    "Red":         (220, 30,  30),
    "Orange":      (255, 140, 0),
    "Yellow":      (240, 220, 0),
    "YellowGreen": (80,  200, 60),
    "Green":       (0,   170, 0),
    "Cyan":        (0,   200, 220),
    "Blue":        (30,  80,  220),
    "Purple":      (160, 0,   200),
    "Pink":        (255, 60,  140),
    "White":       (230, 230, 230),
    "Black":       (40,  40,  40),
    "Unknown":     (160, 160, 160),
}

BOTTLE_CLASS_ID = 39  # COCO class 39 = "bottle"


# ========================
# 3. YOLO model loader (cached)
# ========================
_yolo_model = None

def get_yolo_model(model_name: str = "yolov8n.pt") -> YOLO:
    global _yolo_model
    if _yolo_model is None:
        print(f"Loading YOLO model: {model_name}")
        _yolo_model = YOLO(model_name)
        print("Model loaded.")
    return _yolo_model


# ========================
# 4. Bottle detection
# ========================

def detect_bottles(image_bgr: np.ndarray, conf_threshold: float = 0.4):
    """
    Detect bottles with YOLOv8.

    Returns list of dicts: [{x1, y1, x2, y2, conf}, ...] sorted by confidence desc.
    """
    model = get_yolo_model()
    results = model(image_bgr, verbose=False)[0]

    bottles = []
    for box in results.boxes:
        cls_id = int(box.cls[0])
        conf   = float(box.conf[0])
        if cls_id == BOTTLE_CLASS_ID and conf >= conf_threshold:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            bottles.append({"x1": x1, "y1": y1, "x2": x2, "y2": y2, "conf": conf})

    bottles.sort(key=lambda b: -b["conf"])
    return bottles


# ========================
# 5. Label region crop
# ========================

def crop_label_region(image_bgr: np.ndarray, bottle: dict,
                      margin_top: float = 0.12,
                      margin_bottom: float = 0.12):
    """
    Crop the label area from a bottle bounding box,
    excluding top/bottom margins (cap and base).
    """
    x1, y1, x2, y2 = bottle["x1"], bottle["y1"], bottle["x2"], bottle["y2"]
    bh = y2 - y1
    label_y1 = max(0, int(y1 + bh * margin_top))
    label_y2 = min(image_bgr.shape[0], int(y2 - bh * margin_bottom))
    x1 = max(0, x1)
    x2 = min(image_bgr.shape[1], x2)
    return image_bgr[label_y1:label_y2, x1:x2], (x1, label_y1, x2, label_y2)


# ========================
# 6. Color detection
# ========================

def detect_color(label_bgr: np.ndarray) -> dict:
    """
    Identify the dominant color in the label crop using HSV thresholding.

    Returns dict: {color, confidence, pixel_counts}
    """
    hsv = cv2.cvtColor(label_bgr, cv2.COLOR_BGR2HSV)
    total = hsv.shape[0] * hsv.shape[1]
    kernel = np.ones((3, 3), np.uint8)

    pixel_counts = {}
    for name, ranges in COLOR_RANGES.items():
        mask = np.zeros(hsv.shape[:2], dtype=np.uint8)
        for lower, upper in ranges:
            mask |= cv2.inRange(hsv, lower, upper)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        pixel_counts[name] = int(np.sum(mask > 0))

    best = max(pixel_counts, key=pixel_counts.get)
    conf = pixel_counts[best] / total if total > 0 else 0.0

    if conf < 0.05:
        best, conf = "Unknown", 0.0

    return {"color": best, "confidence": conf, "pixel_counts": pixel_counts}


# ========================
# 7. Main pipeline & visualization
# ========================

def analyze_image(image_bgr: np.ndarray, conf_threshold: float = 0.4):
    """Run bottle detection -> color identification -> visualization on one image."""
    _bottle_cache.clear()
    bottles = detect_bottles(image_bgr, conf_threshold)

    if not bottles:
        print("No bottles detected. Try lowering conf_threshold or use a different image.")
        _show_no_detection(image_bgr)
        return

    print(f"Detected {len(bottles)} bottle(s).")

    n = len(bottles)
    fig = plt.figure(figsize=(6 + n * 5, 10))
    gs  = fig.add_gridspec(2, n + 1, hspace=0.4, wspace=0.3)

    # Top row: full image with bounding boxes
    ax_full = fig.add_subplot(gs[0, :])
    full_rgb = cv2.cvtColor(image_bgr.copy(), cv2.COLOR_BGR2RGB)

    for i, bottle in enumerate(bottles):
        color_result = _process_bottle(image_bgr, bottle)
        color_name   = color_result["color"]
        rgb_c        = tuple(c / 255 for c in COLOR_RGB.get(color_name, (160, 160, 160)))

        x1, y1, x2, y2 = bottle["x1"], bottle["y1"], bottle["x2"], bottle["y2"]
        rect = patches.Rectangle((x1, y1), x2 - x1, y2 - y1,
                                  linewidth=2, edgecolor=rgb_c, facecolor="none")
        ax_full.add_patch(rect)
        ax_full.text(x1, y1 - 6,
                     f"#{i+1} {color_name} ({bottle['conf']*100:.0f}%)",
                     color=rgb_c, fontsize=11, fontweight="bold",
                     bbox=dict(facecolor="black", alpha=0.5, pad=2))

    ax_full.imshow(full_rgb)
    ax_full.set_title("YOLOv8 Bottle Detection", fontsize=13)
    ax_full.axis("off")

    # Bottom row: label crops + bar chart
    for i, bottle in enumerate(bottles):
        color_result = _process_bottle(image_bgr, bottle)
        label_crop, _ = crop_label_region(image_bgr, bottle)
        color_name   = color_result["color"]
        conf         = color_result["confidence"]
        pixel_counts = color_result["pixel_counts"]
        rgb_c        = tuple(c / 255 for c in COLOR_RGB.get(color_name, (160, 160, 160)))

        ax_crop = fig.add_subplot(gs[1, i])
        ax_crop.imshow(cv2.cvtColor(label_crop, cv2.COLOR_BGR2RGB))
        ax_crop.set_title(f"#{i+1} Label Region\n{color_name}  {conf*100:.1f}%",
                          fontsize=11, color=rgb_c)
        ax_crop.axis("off")

        if i == n - 1:
            ax_bar = fig.add_subplot(gs[1, n])
            total  = label_crop.shape[0] * label_crop.shape[1] or 1
            top6   = sorted(pixel_counts.items(), key=lambda x: -x[1])[:6]
            clabels = [c for c, _ in top6]
            values  = [v / total * 100 for _, v in top6]
            bar_colors = [
                tuple(c / 255 for c in COLOR_RGB.get(l, (160, 160, 160)))
                for l in clabels
            ]
            ax_bar.barh(clabels[::-1], values[::-1], color=bar_colors[::-1])
            ax_bar.set_xlabel("Ratio (%)")
            ax_bar.set_title(f"#{i+1} Color Ratio (Top 6)", fontsize=10)

    plt.show()

    print("\n===== Detection Summary =====")
    for i, bottle in enumerate(bottles):
        r = _process_bottle(image_bgr, bottle)
        print(f"  Bottle #{i+1}: {r['color']}  "
              f"(color conf: {r['confidence']*100:.1f}%,  "
              f"YOLO conf: {bottle['conf']*100:.0f}%)")


# Internal cache helper
_bottle_cache: dict = {}

def _process_bottle(image_bgr, bottle):
    key = (bottle["x1"], bottle["y1"], bottle["x2"], bottle["y2"])
    if key not in _bottle_cache:
        label_crop, _ = crop_label_region(image_bgr, bottle)
        _bottle_cache[key] = detect_color(label_crop)
    return _bottle_cache[key]


def _show_no_detection(image_bgr):
    plt.figure(figsize=(8, 5))
    plt.imshow(cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB))
    plt.title("No bottle detected", color="red", fontsize=13)
    plt.axis("off")
    plt.show()


# ========================
# 8. Synthetic demo (no real image needed)
# ========================

def demo_synthetic():
    """Run a quick sanity check using synthetic bottle images."""
    _bottle_cache.clear()

    test_cases = [
        ("Red label",    (30,  30,  200)),
        ("Blue label",   (200, 80,  30)),
        ("Green label",  (30,  180, 30)),
        ("Yellow label", (30,  220, 230)),
    ]

    for title, bgr_color in test_cases:
        print(f"\n=== Synthetic test: {title} ===")
        img = np.ones((480, 320, 3), dtype=np.uint8) * 230
        img[60:400,  70:250] = bgr_color       # label
        img[0:60,    70:250] = (200, 200, 200) # cap
        img[400:480, 70:250] = (180, 180, 180) # base

        fake_bottle = {"x1": 70, "y1": 0, "x2": 250, "y2": 480, "conf": 1.0}
        label_crop, _ = crop_label_region(img, fake_bottle)
        result = detect_color(label_crop)

        fig, axes = plt.subplots(1, 2, figsize=(10, 4))
        axes[0].imshow(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        axes[0].set_title(f"{title}\n-> Detected: {result['color']}  "
                          f"{result['confidence']*100:.1f}%")
        axes[0].axis("off")

        total  = label_crop.shape[0] * label_crop.shape[1] or 1
        top6   = sorted(result["pixel_counts"].items(), key=lambda x: -x[1])[:6]
        clabels = [c for c, _ in top6]
        values  = [v / total * 100 for _, v in top6]
        bar_colors = [tuple(c/255 for c in COLOR_RGB.get(l, (160,160,160))) for l in clabels]
        axes[1].barh(clabels[::-1], values[::-1], color=bar_colors[::-1])
        axes[1].set_xlabel("Ratio (%)")
        axes[1].set_title("Color Ratio (Top 6)")
        plt.tight_layout()
        plt.show()


# ========================
# 9. Entry point
# ========================
if __name__ == "__main__":
    # [A] Synthetic demo (no image required, no YOLO)
    demo_synthetic()

    # [B] Upload an image and analyze with YOLO
    # uploaded = files.upload()
    # for filename, data in uploaded.items():
    #     arr = np.frombuffer(data, dtype=np.uint8)
    #     img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    #     analyze_image(img)

    # [C] Load from Google Drive
    # from google.colab import drive
    # drive.mount('/content/drive')
    # img = cv2.imread('/content/drive/MyDrive/bottle.jpg')
    # analyze_image(img)
