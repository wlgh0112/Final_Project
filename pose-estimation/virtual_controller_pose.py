"""
포즈(손 키포인트) 기반 가상 컨트롤러.
기존 virtual_controller(best.pt 검출 방식)와 같은 KEYMAP / COOLDOWN / 연속 프레임 로직을 쓰되,
제스처 판정만 [포즈 모델 -> 분류기]로 바꾼 버전. pose_gesture.py와 같은 폴더에 두세요.

실행 예:
  python virtual_controller_pose.py --pose runs/pose/train/weights/best.pt --clf gesture_clf.joblib --dry-run
  python virtual_controller_pose.py --pose ... --clf ... --det best.pt     # 기존 검출 모델과 일치할 때만 입력
"""
import argparse
import time

from pose_gesture import kpts_to_feat, pick_device

# ----------------------------------------------------------------
# [설정 영역] 클래스 이름은 분류기의 클래스(hand4의 names)와 일치해야 합니다.
# ----------------------------------------------------------------
KEYMAP = {"left": "left", "right": "right", "fist": "esc", "palm": "f5"}
COOLDOWN = {"left": 0.8, "right": 0.8, "fist": 1.5, "palm": 1.5}
STREAK_THRESHOLD = 3
# ----------------------------------------------------------------


class Trigger:
    """연속 프레임 + 쿨다운 판정. 누를 키가 있으면 키 이름을, 아니면 None을 반환."""

    def __init__(self, keymap, cooldown, streak_n):
        self.keymap, self.cooldown, self.streak_n = keymap, cooldown, streak_n
        self.last = {k: float("-inf") for k in keymap}
        self.cls, self.count = None, 0

    def update(self, label, now):
        # 손이 사라지거나 불확실하면 연속 카운트를 리셋 (기존 코드는 리셋이 없었음)
        if label in (None, "unknown"):
            self.cls, self.count = None, 0
            return None
        if label == self.cls:
            self.count += 1
        else:
            self.cls, self.count = label, 1
        if (label in self.keymap and self.count >= self.streak_n
                and now - self.last[label] > self.cooldown[label]):
            self.last[label] = now
            return self.keymap[label]
        return None


def run(a):
    import cv2
    import joblib
    import pyautogui
    from ultralytics import YOLO

    pack = joblib.load(a.clf)
    clf, names = pack["clf"], pack["names"]
    dev = pick_device(a.device)
    pose = YOLO(a.pose)
    det = YOLO(a.det) if a.det else None
    print(f"✅ 로드 완료 | 클래스: {names} | 일치 검증 모드: {'ON' if det else 'OFF'} | dry-run: {a.dry_run}")

    cap = cv2.VideoCapture(a.cam)
    if not cap.isOpened():
        print("❌ 웹캠을 열 수 없습니다.")
        return
    trig = Trigger(KEYMAP, COOLDOWN, a.streak)
    print("🚀 시작! 종료: 'q'")

    try:
        while cap.isOpened():
            ok, frame = cap.read()
            if not ok:
                break
            if not a.no_mirror:
                frame = cv2.flip(frame, 1)   # 기존 코드와 동일한 거울 모드

            res = pose.predict(frame, conf=a.conf, imgsz=a.imgsz, device=dev, verbose=False)[0]
            shown = res.plot(labels=False)
            label, prob = None, 0.0

            if res.boxes is not None and len(res.boxes) > 0 and res.keypoints is not None:
                i = int(res.boxes.conf.argmax())
                kp = res.keypoints.xy[i].cpu().numpy()
                proba = clf.predict_proba([kpts_to_feat(kp)])[0]
                j = int(proba.argmax())
                prob = float(proba[j])
                label = names[j] if prob >= a.thr else "unknown"

                # 선택: 기존 검출 모델과 결과가 같을 때만 인정 (오작동 방지)
                if det is not None and label != "unknown":
                    dr = det(frame, conf=a.det_conf, device=dev, verbose=False)[0]
                    det_label = None
                    if len(dr.boxes) > 0:
                        det_label = det.names[int(dr.boxes.cls[dr.boxes.conf.argmax()])]
                    if det_label != label:
                        label = "unknown"

                x1, y1 = map(int, res.boxes.xyxy[i][:2].tolist())
                cv2.putText(shown, f"{label} {prob:.2f}", (x1, max(y1 - 8, 15)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

            key = trig.update(label, time.time())
            if key:
                if not a.dry_run:
                    pyautogui.press(key)
                cv2.putText(shown, f"PRESSED: {key.upper()}" + (" (dry)" if a.dry_run else ""),
                            (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                print(f"[{time.strftime('%H:%M:%S')}] {label} -> {key}")

            cv2.imshow("Virtual Controller (pose)", shown)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()
        print("👋 컨트롤러를 종료합니다.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--pose", required=True, help="포즈 모델 가중치 (best.pt)")
    ap.add_argument("--clf", default="gesture_clf.joblib")
    ap.add_argument("--det", default=None, help="기존 검출 모델(best.pt). 주면 두 모델 결과가 같을 때만 입력")
    ap.add_argument("--cam", type=int, default=0)
    ap.add_argument("--imgsz", type=int, default=640)
    ap.add_argument("--conf", type=float, default=0.5)
    ap.add_argument("--det-conf", dest="det_conf", type=float, default=0.5)
    ap.add_argument("--thr", type=float, default=0.7, help="분류 확률 하한 (미만이면 unknown)")
    ap.add_argument("--streak", type=int, default=STREAK_THRESHOLD)
    ap.add_argument("--no-mirror", action="store_true")
    ap.add_argument("--device", default="auto", help="auto(GPU 우선) | 0 | cpu")
    ap.add_argument("--dry-run", action="store_true", help="키 입력 없이 인식 결과만 확인")
    run(ap.parse_args())
