# Final_Project
오픈소스 SW프로그래밍 기말 프로젝트
20231074 채지호
20231060 손하민
20251066 조현빈

#팀원 모두 가상환경 맞추기 위한 공통 세팅 과정
#아래에 있는 명령어들을 vscode터미널에 순서대로 복사해서 붙여넣기

1. 아나콘다 가상환경 테두리 만들기(yolo26이라는 환경 만들기)
conda create -n yolo26 python=3.11 -y
conda activate yolo26

2. 모델 학습에 필요한 가상환경 구축 명령어
python -m pip install -U ultralytics "numpy==1.26.4" "opencv-python==4.11.0.86"
pip install pyyaml roboflow
python -m pip install roboflow

3. GPU를 사용하여 학습시키기 위해 GPU용 파이토치 만들기
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121



실행 명령어 
cd C:\Users\user\Desktop\yolo(모델이 있는 경로)
python train.py(욜로모델)

# 학습 파일(train.py) 실행 명령어
$env:ROBOFLOW_API_KEY="여기에_복사한_API키_붙여넣기"; python train.py

마우스와 키보드를 대신 조작하는 라이브러리
pip install pyautogui

# 이때 data.yaml 파일을 올려놓을예정이고, 데이터셋이 들어있는 파일이름은 DataSet 파일이름으로 해결. 
