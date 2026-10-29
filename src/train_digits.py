import sys, shutil, os
from ultralytics import YOLO

def main():
    epochs = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    model = YOLO("yolov8n.pt")
    model.train(
        data="config/digits.yaml",
        epochs=epochs,
        imgsz=416,
        batch=16,           # use 8 if you get an out-of-memory error
        device=0,
        patience=30,
        workers=0,
        fliplr=0.0,         # mirroring would turn 2 into 5 and so on
        flipud=0.0,
        degrees=10,
        perspective=0.0005,
        hsv_v=0.5,
        project="runs",
        name="digits_v1",
        exist_ok=True,
    )
    best = os.path.join(str(model.trainer.save_dir), "weights", "best.pt")
    print("Best weights:", best)
    os.makedirs("models", exist_ok=True)
    shutil.copy(best, os.path.join("models", "digits.pt"))
    m = YOLO(os.path.join("models", "digits.pt")).val(
        data="config/digits.yaml", split="test", device=0, workers=0)
    print("TEST mAP50:", round(m.box.map50, 3), " mAP50-95:", round(m.box.map, 3),
          " precision:", round(m.box.mp, 3), " recall:", round(m.box.mr, 3))

if __name__ == "__main__":
    main()