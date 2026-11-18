import cv2
import time
import argparse
import pyautogui
from ultralytics import YOLO

# ----------------------------------------------------------------
# [설정 영역]
# ----------------------------------------------------------------
# 동작과 키 매핑 (모델의 클래스 이름과 일치해야 합니다)
KEYMAP = {
    "left": "left",    # ← 화살표
    "right": "right",  # → 화살표
    "fist": "esc",     # Esc
    "palm": "f5"       # F5
}

# 연속 입력을 방지하기 위한 쿨다운 (초)
# 너무 빠르면 키가 미친듯이 눌리므로 적절한 값을 설정하세요.
COOLDOWN = {
    "left": 0.8,
    "right": 0.8,
    "fist": 1.5,
    "palm": 1.5
}

# 동작이 연속적으로 유지되어야 인식되는 프레임 수
STREAK_THRESHOLD = 3 
# ----------------------------------------------------------------

def run_webcam():
    # 1. 모델 불러오기 (사용자가 입력한 경로 사용)
    model_path = "best.pt"
    try:
        model = YOLO(model_path)
        print(f"✅ 모델 로드 성공: {model_path}")
    except Exception as e:
        print(f"❌ 모델 로드 실패: {e}")
        print("경로가 맞는지 확인하세요.")
        return

    # 모델의 클래스 이름 가져오기
    names = model.names
    print(f"📋 인식 가능한 클래스: {names}")

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ 웹캠을 열 수 없습니다.")
        return

    # 입력 제어 변수
    last_press_time = {k: 0.0 for k in KEYMAP.keys()} # 마지막 입력 시간
    streak_cls = None                                 # 현재 연속된 클래스
    streak_count = 0                                 # 연속 카운트
    
    print("\n🚀 컨트롤러 시작!")
    print("   - 동작: left(←), right(→), fist(Esc), palm(F5)")
    print("   - 종료: 'q' 키를 누르세요.")

    try:
        while cap.isOpened():
            success, frame = cap.read()
            if not success:
                break

            # [중요] 거울 모드로 화면 반전 (사용자 편의성)
            frame = cv2.flip(frame, 1)

            # 모델 추론
            results = model(frame, conf=0.5, verbose=False)
            
            current_best_cls = None
            max_conf = 0

            # 결과 처리
            for r in results:
                annotated_frame = r.plot()
                
                # 가장 신뢰도가 높은 박스 하나만 선택
                if len(r.boxes) > 0:
                    # 가장 높은 confidence를 가진 인덱스 찾기
                    idx = r.boxes.conf.argmax()
                    conf = float(r.boxes.conf[idx])
                    cls_id = int(r.boxes.cls[idx])
                    current_best_cls = names[cls_id]
                    max_conf = conf

                    # --- [키보드 입력 로직 시작] ---
                    # 1. 동일 동작이 연속으로 나타나는지 확인 (노이즈 방지)
                    if current_best_cls == streak_cls:
                        streak_count += 1
                    else:
                        streak_cls = current_best_cls
                        streak_count = 1

                    # 2. 조건 확인: 연속성 통과 AND 쿨다운 통과 AND 매핑된 키 존재
                    if (streak_count >= STREAK_THRESHOLD and 
                        current_best_cls in KEYMAP and 
                        (time.time() - last_press_time[current_best_cls]) > COOLDOWN[current_best_cls]):
                        
                        # 실제 키 입력
                        pyautogui.press(KEYMAP[current_best_cls])
                        last_press_time[current_best_cls] = time.time()
                        
                        # 화면에 알림 표시
                        cv2.putText(annotated_frame, f"PRESSED: {current_best_cls.upper()}", 
                                    (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                    # --- [키보드 입력 로직 끝] ---

                cv2.imshow("Virtual Controller", annotated_frame)
            
            # 만약 아무것도 안 잡혔다면 빈 화면이라도 보여줌
            if len(results) == 0 or len(results[0].boxes) == 0:
                cv2.imshow("Virtual Controller", frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    except Exception as e:
        print(f"⚠️ 오류 발생: {e}")
    finally:
        cap.release()
        cv2.destroyAllWindows()
        print("👋 컨트롤러를 종료합니다.")

if __name__ == '__main__':
    run_webcam()
