import sys, shutil, os
from ultralytics import YOLO

def main():
    epochs = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    model = YOLO("yolov8n.pt")          # small pretrained model
    model.train(
        data="config/display.yaml",
        epochs=epochs,
        imgsz=640,
        batch=8,            # use 4 if you get an out-of-memory error
        device=0,
        patience=30,        # stop early if validation stops improving
        workers=0,          # avoids multiprocessing problems on Windows
        fliplr=0.0,         # never mirror meter displays
        degrees=10,         # small rotation augmentation
        project="runs",
        name="display_v1",
        exist_ok=True,
    )

    # Ask Ultralytics where it really saved the weights
    best = os.path.join(str(model.trainer.save_dir), "weights", "best.pt")
    print("Best weights:", best)
    os.makedirs("models", exist_ok=True)
    shutil.copy(best, os.path.join("models", "display.pt"))

    # Final score on the held-out test split
    metrics = YOLO(os.path.join("models", "display.pt")).val(
        data="config/display.yaml", split="test", device=0, workers=0)
    print("TEST mAP50:", round(metrics.box.map50, 3),
          " mAP50-95:", round(metrics.box.map, 3),
          " precision:", round(metrics.box.mp, 3),
          " recall:", round(metrics.box.mr, 3))

if __name__ == "__main__":
    main()