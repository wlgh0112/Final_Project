from ultralytics import YOLO


def main():
    # 사전학습 모델에서 시작
    model = YOLO("yolo26n.pt")

    model.train(
        data="data.yaml",
        epochs=1,
        imgsz=640,
        batch=2,
        device="cpu",       # GPU가 없으면 "cpu"로 변경
        project="runs",
        name="four_classes",
    )


if __name__ == "__main__":
    main()
