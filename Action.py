"""슬라이드쇼 제어: 키 입력 방식 (PowerPoint / PDF 뷰어 / 구글 슬라이드 공통).
키 입력은 '맨 앞 창'으로 가므로, 보내기 전에 PPT 창을 앞으로 가져온다."""
import time

import pyautogui

import config
from winutil import find_window, focus_window, foreground_window

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
        if config.FORCE_FOCUS_PRESENTATION:
            self._focus_presentation()
        pyautogui.press(key)
        print(f"[ACTION] {action} -> {key}")
        return True

    def _focus_presentation(self):
        hwnd = find_window(config.PRESENTATION_WINDOW_KEYWORDS)
        if hwnd and hwnd != foreground_window():
            focus_window(hwnd)
            time.sleep(0.05)     # 창 전환 직후 키 유실 방지