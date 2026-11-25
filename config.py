"""설정 모음. 팀원이 코드 건드리지 않고 여기만 수정하면 되도록 분리."""

# 모델 경로 찾기
import subprocess
from pathlib import Path

DEFAULT_MODEL_PATH = "runs/detect/train-6/weights/best.pt"


def resolve_model_path(default_path: str = DEFAULT_MODEL_PATH) -> str:
    # 1순위: 클립보드에 실제 존재하는 .pt 파일 경로가 들어있는 경우
    try:
        clip = subprocess.check_output(
            ["powershell", "-NoProfile", "-Command", "Get-Clipboard"],
            text=True,
            timeout=3,
        ).strip().strip('"')
        if clip.lower().endswith(".pt") and Path(clip).is_file():
            return clip
    except Exception:
        pass

    # 2순위: 클립보드가 다른 내용으로 덮였다면 runs/detect 아래 최신 best.pt 자동 탐색
    candidates = list(Path("runs/detect").glob("**/weights/best.pt"))
    if candidates:
        latest = max(candidates, key=lambda p: p.stat().st_mtime)
        return str(latest)

    # 3순위: 기존 기본 경로 사용
    return default_path


# ---------- 모델 / 카메라 ----------
MODEL_PATH = resolve_model_path()
# ---------- 모델 / 카메라 ----------
CAMERA_INDEX = 0
FRAME_W, FRAME_H = 640, 480
CONF_THRESHOLD = 0.5
IMGSZ = 640
MIRROR = True                 # 거울 모드(좌우 반전) - 손 움직임 방향 직관화
SHOW_PREVIEW = True           # 디버그용 카메라 창 (q 누르면 종료)

# ---------- 좌표 변환 ----------
ROI_MARGIN = 0.15             # 카메라 가장자리 15%는 무시 (손이 화면 끝까지 닿기 쉽게)
SMOOTHING_ALPHA = 0.35        # EMA 계수 (작을수록 부드럽고 느림)

# ---------- 제스처 안정화 ----------
CONFIRM_FRAMES = 5            # 같은 라벨이 N프레임 연속이어야 확정 (오인식 방지)
COOLDOWN_SEC = 0.8            # 이산 동작(다음/이전 등) 재발동 대기 시간

# ---------- 제스처 라벨 -> 동작 매핑 ----------
# 키는 data.yaml의 names와 정확히 일치해야 함! (YOLO 파트장과 합의 필요)
# 동작: next, prev, start, end, clear (이산) / pointer, draw (연속)
GESTURE_ACTIONS = {
    "right": "next",      # 다음 슬라이드
    "left":  "prev",      # 이전 슬라이드
    "palm":  "pointer",   # 레이저 포인터
    "fist":  "clear",     # 판서 지우기 (또는 원하는 동작)
}
# 화면에 잠깐 뜨는 안내 문구
ACTION_LABELS = {
    "next": "다음 슬라이드 ▶", "prev": "◀ 이전 슬라이드",
    "start": "슬라이드쇼 시작", "end": "슬라이드쇼 종료",
    "clear": "판서 지우기", "pointer": "레이저 포인터", "draw": "판서 모드",
}
TOAST_MS = 1400

# 동작별 색상 (상단 팝업, 하단 상태창, 카메라 미리보기에서 공통 사용)
ACTION_COLORS = {
    "next": "#16a34a", "prev": "#0891b2",
    "start": "#7c3aed", "end": "#7c3aed",
    "clear": "#6b7280", "pointer": "#dc2626", "draw": "#f59e0b",
}
IDLE_COLOR = "#6b7280"

CONTINUOUS_ACTIONS = {"pointer", "draw"}
DISCRETE_ACTIONS = {"next", "prev", "start", "end", "clear"}

# ---------- 오버레이 스타일 ----------
POINTER_COLOR = "red"
POINTER_RADIUS = 16
PEN_COLOR = "#ff3b30"
PEN_WIDTH = 7