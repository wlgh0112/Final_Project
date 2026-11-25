
"""설정 모음. 팀원이 코드 건드리지 않고 여기만 수정하면 되도록 분리."""
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_MODEL_PATH = "runs/detect/train/weights/best.pt"


def resolve_model_path(default_path: str = DEFAULT_MODEL_PATH) -> str:
    """모델(best.pt) 경로 자동 탐색. 팀원마다 경로가 달라도 이 파일을 안 고쳐도 됨."""
    # 1순위: train.py가 학습 직후 남긴 latest_model.txt
    for base in (BASE_DIR, Path.cwd()):
        f = base / "latest_model.txt"
        try:
            if f.is_file():
                p = f.read_text(encoding="utf-8").strip().strip('"')
                if p.lower().endswith(".pt") and Path(p).is_file():
                    return p
        except Exception:
            pass

    # 2순위: 클립보드에 실제 존재하는 .pt 파일 경로가 들어있는 경우
    try:
        clip = subprocess.check_output(
            ["powershell", "-NoProfile", "-Command", "Get-Clipboard"],
            text=True, timeout=3,
        ).strip().strip('"')
        if clip.lower().endswith(".pt") and Path(clip).is_file():
            return clip
    except Exception:
        pass

    # 3순위: runs/detect 아래 가장 최근에 만들어진 best.pt
    candidates = []
    for base in (BASE_DIR, Path.cwd()):
        candidates += list((base / "runs" / "detect").glob("**/weights/best.pt"))
    if candidates:
        return str(max(candidates, key=lambda p: p.stat().st_mtime))

    # 4순위: 기본 경로
    return default_path


# ---------- 모델 / 카메라 ----------
MODEL_PATH = resolve_model_path()
print(f"[CONFIG] 사용할 모델: {MODEL_PATH}")
CAMERA_INDEX = 0
FRAME_W, FRAME_H = 640, 480
CONF_THRESHOLD = 0.5
IMGSZ = 640
MIRROR = True
SHOW_PREVIEW = True
PREVIEW_W, PREVIEW_H = 400, 300

# ---------- 좌표 변환 ----------
ROI_MARGIN = 0.15
SMOOTHING_ALPHA = 0.35

# ---------- 제스처 안정화 ----------
CONFIRM_FRAMES = 5
COOLDOWN_SEC = 0.8

# ---------- 제스처 라벨 -> 동작 매핑 ----------
GESTURE_ACTIONS = {
    "right": "prev",
    "left": "next",
    "palm": "start",
    "fist": "end",
}

# ---------- 화면에 잠깐 뜨는 안내 문구 ----------
ACTION_LABELS = {
    "next": "다음 슬라이드 ▶", "prev": "◀ 이전 슬라이드",
    "start": "슬라이드쇼 시작", "end": "슬라이드쇼 종료",
    "clear": "판서 지우기", "pointer": "레이저 포인터", "draw": "판서 모드",
}
TOAST_MS = 1400

# ---------- 동작별 색상 ----------
ACTION_COLORS = {
    "next": "#16a34a", "prev": "#0891b2",
    "start": "#7c3aed", "end": "#dc2626",
    "clear": "#6b7280", "pointer": "#dc2626", "draw": "#f59e0b",
}
IDLE_COLOR = "#6b7280"

# ---------- 작은 동작 표시 창 (panel.py) ----------
PANEL_W, PANEL_H = 400, 150
PANEL_COMPACT_W, PANEL_COMPACT_H = 240, 64
PANEL_IDLE_ALPHA = 0.6
PANEL_ACTIVE_ALPHA = 1.0
PANEL_ANIM_MS = 100
PANEL_FLASH_MS = 1500
SHOW_TOAST = False

# ---------- PPT 연동 ----------
FORCE_FOCUS_PRESENTATION = True
PRESENTATION_WINDOW_KEYWORDS = ["슬라이드 쇼", "Slide Show", "PowerPoint"]

CONTINUOUS_ACTIONS = {"pointer", "draw"}
DISCRETE_ACTIONS = {"next", "prev", "start", "end", "clear"}

# ---------- 오버레이 스타일 ----------
POINTER_COLOR = "red"
POINTER_RADIUS = 16
PEN_COLOR = "#ff3b30"
PEN_WIDTH = 7

# ---------- 카메라 상태 표시 ----------
SHOW_CAMERA_STATUS = True

CAMERA_STATUS_LABELS = {
    "connected": "CAMERA CONNECTED",
    "disconnected": "CAMERA DISCONNECTED",
}

CAMERA_STATUS_COLORS = {
    "connected": "#16a34a",
    "disconnected": "#dc2626",
}