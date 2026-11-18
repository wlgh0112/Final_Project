import cv2
from ultralytics import YOLO

def run_webcam():
    # 방금 성공적으로 저장된 1에폭 학습 결과물(best.pt)을 불러옵니다.
    # 터미널에 출력된 저장 경로를 바탕으로 설정했습니다.
    model = YOLO("runs/detect/runs/four_classes-9/weights/best.pt")

    cap = cv2.VideoCapture(0) # 0번(기본) 웹캠 연결

    while cap.isOpened():
        success, frame = cap.read()
        if not success:
            break

        # 거울처럼 보이도록 화면 좌우 반전
        frame = cv2.flip(frame, 1)

        # 모델 추론 수행 (RTX 3060이 자동으로 화면을 초고속 분석합니다)
        results = model(frame, stream=True)

        # 분석 결과를 화면에 박스로 그려서 띄우기
        for r in results:
            annotated_frame = r.plot()
            cv2.imshow("Virtual Controller - 1 Epoch Test", annotated_frame)

        # 'q' 키를 누르면 웹캠 창 닫기 및 종료
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == '__main__':
    run_webcam()