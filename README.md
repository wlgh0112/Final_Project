# Final_Project
오픈소스 SW프로그래밍 기말 프로젝트
20231074 채지호
20231060 손하민
20251066 조현빈

# 가상환경 구축
python -m pip install -U ultralytics "numpy==1.26.4" "opencv-python==4.11.0.86"

-아나콘다에서 실행
conda create -n yolo26 python=3.11 -y
conda activate yolo26

cd C:\Users\user\Desktop\yolo(모델이 있는 경로)
python train.py(욜로모델)

모델 돌릴때
파일안에 모델,데이터셋(test,train,valid),data.yaml 같이 있어야함