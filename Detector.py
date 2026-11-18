"""YOLO 파트와의 접점. UI 쪽은 이 파일의 Detection만 사용한다."""
from dataclasses import dataclass
from typing import Optional

from ultralytics import YOLO

import config


@dataclass
class Detection:
    label: str
    conf: float
    cx: float          # 바운딩 박스 중심 (프레임 픽셀 좌표)
    cy: float
    bbox: tuple        # (x1, y1, x2, y2)


class HandDetector:
    def __init__(self, model_path: str = config.MODEL_PATH):
        self.model = YOLO(model_path)

    def check_mapping(self):
        """모델 클래스 이름과 config.GESTURE_ACTIONS가 맞는지 시작할 때 점검."""
        names = list(self.model.names.values())
        print("[MODEL] 클래스:", names)
        for n in names:
            if n not in config.GESTURE_ACTIONS:
                print(f"[WARN] '{n}' 은(는) GESTURE_ACTIONS에 없음 -> 이 제스처는 동작 안 함")
        for k in config.GESTURE_ACTIONS:
            if k not in names:
                print(f"[WARN] GESTURE_ACTIONS의 '{k}' 은(는) 모델에 없는 라벨")

    def detect(self, frame) -> Optional[Detection]:
        """프레임에서 가장 신뢰도 높은 손 1개를 반환. 없으면 None."""
        res = self.model.predict(
            frame, conf=config.CONF_THRESHOLD, imgsz=config.IMGSZ, verbose=False
        )[0]
        if res.boxes is None or len(res.boxes) == 0:
            return None
        i = int(res.boxes.conf.argmax())
        x1, y1, x2, y2 = res.boxes.xyxy[i].tolist()
        return Detection(
            label=res.names[int(res.boxes.cls[i])],
            conf=float(res.boxes.conf[i]),
            cx=(x1 + x2) / 2,
            cy=(y1 + y2) / 2,
            bbox=(x1, y1, x2, y2),
        )