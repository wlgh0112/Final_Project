"""슬라이드쇼 제어 (PowerPoint / 한컴 / PDF 뷰어 / 구글 슬라이드 공통: 키보드 입력 방식)."""
import pyautogui

pyautogui.PAUSE = 0
pyautogui.FAILSAFE = True   # 마우스를 화면 모서리로 던지면 긴급 중단

KEY_MAP = {
    "next": "right",
    "prev": "left",
    "start": "f5",
    "end": "esc",
}


class SlideController:
    def do(self, action: str) -> bool:
        """키 입력으로 처리되는 동작이면 실행 후 True. (clear 등은 오버레이 담당)"""
        key = KEY_MAP.get(action)
        if key is None:
            return False
        pyautogui.press(key)
        print(f"[ACTION] {action} -> {key}")
        return True