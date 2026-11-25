"""실행: python main.py
구조: [카메라+YOLO 스레드] --queue--> [Tk 오버레이/동작창/카메라창 (메인 스레드)]
"""
import ctypes
import queue
import threading
import traceback

import cv2

import config
from Action import SlideController
from Coords import CoordMapper
from Detector import HandDetector, Detection
from Overlay import Overlay
from preview import PreviewWindow, Shared
from Stabilizer import GestureStabilizer


def hex_to_bgr(h: str):
    h = h.lstrip("#")
    return int(h[4:6], 16), int(h[2:4], 16), int(h[0:2], 16)


def open_camera(shared: Shared):
    """설정된 번호부터 0~3번 카메라를 여러 방식으로 시도해서 열린 것을 반환."""
    indexes = [config.CAMERA_INDEX] + [i for i in range(4) if i != config.CAMERA_INDEX]
    for idx in indexes:
        for backend in (cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY):
            shared.message = f"카메라 연결 중... (번호 {idx})"
            cap = cv2.VideoCapture(idx, backend)
            if cap.isOpened():
                ok, _ = cap.read()
                if ok:
                    cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.FRAME_W)
                    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.FRAME_H)
                    print(f"[CAMERA] 연결 성공: 번호 {idx}, backend {backend}")
                    return cap
            cap.release()
    return None


def vision_loop(events: queue.Queue, stop: threading.Event, shared: Shared,
                screen_w: int, screen_h: int):
    cap = None
    try:
        shared.message = "모델 불러오는 중... (처음엔 몇 초 걸려요)"
        detector = HandDetector()
        detector.check_mapping()
        stab = GestureStabilizer()
        ctrl = SlideController()
        mapper = CoordMapper(config.FRAME_W, config.FRAME_H, screen_w, screen_h)

        cap = open_camera(shared)
        if cap is None:
            msg = ("카메라를 열 수 없습니다.\n"
                   "- 다른 앱(줌, 카톡 등)이 카메라를 쓰는 중인지 확인\n"
                   "- 윈도우 설정 > 개인정보 > 카메라 허용 확인")
            print("[ERROR]", msg)
            shared.message = msg
            return

        was_continuous = False
        last_cont = None
        fail = 0
        while not stop.is_set():
            ok, frame = cap.read()
            if not ok:
                fail += 1
                if fail > 30:
                    shared.message = "카메라 영상을 읽지 못하고 있어요."
                    shared.frame = None
                continue
            fail = 0
            if config.MIRROR:
                frame = cv2.flip(frame, 1)

            det = detector.detect(frame)
            raw = det.label if det else None
            label, is_new = stab.update(raw)
            action = config.GESTURE_ACTIONS.get(label)

            if action in config.CONTINUOUS_ACTIONS and det:
                if action != last_cont:
                    events.put(("toast", config.ACTION_LABELS[action], config.ACTION_COLORS[action]))
                    last_cont = action
                x, y = mapper.map(det.cx, det.cy)
                events.put((action, x, y))
                was_continuous = True
            else:
                if was_continuous:
                    events.put(("idle",))
                    mapper.reset()
                    was_continuous = False
                    last_cont = None
                if is_new and action in config.DISCRETE_ACTIONS:
                    if action == "clear":
                        events.put(("clear",))
                    else:
                        ctrl.do(action)
                    events.put(("toast", config.ACTION_LABELS[action], config.ACTION_COLORS[action]))

            events.put(("status", raw, action, stab.progress))

            if config.SHOW_PREVIEW:
                shared.frame = draw_preview(frame, det, action, stab.progress)

    except Exception as e:                      # 에러를 화면에도 표시 (터미널만 보면 놓침)
        traceback.print_exc()
        shared.frame = None
        shared.message = f"오류 발생:\n{type(e).__name__}: {e}"
    finally:
        if cap is not None:
            cap.release()


def draw_preview(frame, det: "Detection | None", action, progress):
    """인식 결과를 그린 프레임을 반환."""
    h, w = frame.shape[:2]
    color = hex_to_bgr(config.ACTION_COLORS.get(action, config.IDLE_COLOR))

    if det:
        x1, y1, x2, y2 = map(int, det.bbox)
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 4)
        tag = f"{det.label} {det.conf:.2f}"
        (tw, th), _ = cv2.getTextSize(tag, cv2.FONT_HERSHEY_SIMPLEX, 0.9, 2)
        cv2.rectangle(frame, (x1, max(y1 - th - 14, 0)), (x1 + tw + 10, max(y1, th + 14)), color, -1)
        cv2.putText(frame, tag, (x1 + 5, max(y1 - 8, th + 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.9,
                    (255, 255, 255), 2, cv2.LINE_AA)

    cv2.rectangle(frame, (0, 0), (w, 44), (17, 24, 39), -1)
    status = f"action: {action}" if action else ("checking..." if det else "no hand")
    cv2.putText(frame, status, (12, 31), cv2.FONT_HERSHEY_SIMPLEX, 0.95,
                (255, 255, 255), 2, cv2.LINE_AA)
    cv2.rectangle(frame, (0, 44), (w, 52), (55, 65, 81), -1)
    cv2.rectangle(frame, (0, 44), (int(w * progress), 52), color, -1)
    return frame


def main():
    ctypes.windll.shcore.SetProcessDpiAwareness(1)   # 고DPI 화면 좌표 어긋남 방지 (Tk 생성 전)

    events: queue.Queue = queue.Queue()
    stop = threading.Event()
    shared = Shared()

    overlay = Overlay(events, stop)
    if config.SHOW_PREVIEW:
        PreviewWindow(overlay.root, stop, shared)

    t = threading.Thread(
        target=vision_loop, args=(events, stop, shared, overlay.sw, overlay.sh), daemon=True
    )
    t.start()
    try:
        overlay.run()
    finally:
        stop.set()


if __name__ == "__main__":
    main()