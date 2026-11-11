from ultralytics import YOLO
import torch
import cv2

# 1. YOLO26n 모델 로드 (최초 실행 시 자동으로 yolo26n.pt 파일이 다운로드됨)
model = YOLO("yolo26n.pt")

# 2. 장착된 RTX 5080 GPU가 모델의 연산에 정상적으로 연결(가속)되었는지 확인
print("GPU 사용 가능 여부:", torch.cuda.is_available())

# 3. 웹캠 테스트 (숫자 0은 기본 내장/연결된 웹캠을 의미)
cap = cv2.VideoCapture(0)

while cap.isOpened():
    success, frame = cap.read()
    if not success:
        break

    # 프레임마다 YOLO 모델로 객체 탐지 수행
    results = model(frame, stream=True)

    # 인식된 결과를 화면에 네모 박스로 그려서 보여주기
    for r in results:
        annotated_frame = r.plot()
        cv2.imshow("YOLO26n Webcam Test", annotated_frame)

    # 'q' 키를 누르면 종료
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()