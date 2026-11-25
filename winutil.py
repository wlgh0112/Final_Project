"""Windows 창 제어 도구 (ctypes). PPT 창 찾기/앞으로 가져오기, 창 스타일 설정."""
import ctypes
from ctypes import wintypes

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x80000
WS_EX_TRANSPARENT = 0x20
WS_EX_NOACTIVATE = 0x08000000   # 클릭해도 포커스를 가져가지 않음
WS_EX_TOOLWINDOW = 0x80          # 작업표시줄/Alt+Tab에 안 나옴
SW_RESTORE = 9


def set_ex_style(widget, flags: int):
    """tkinter 창에 확장 스타일 추가."""
    hwnd = user32.GetParent(widget.winfo_id()) or widget.winfo_id()
    style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style | flags)


def _list_windows():
    out = []
    enum_proc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def cb(hwnd, _):
        if user32.IsWindowVisible(hwnd):
            n = user32.GetWindowTextLengthW(hwnd)
            if n > 0:
                buf = ctypes.create_unicode_buffer(n + 1)
                user32.GetWindowTextW(hwnd, buf, n + 1)
                out.append((hwnd, buf.value))
        return True

    user32.EnumWindows(enum_proc(cb), 0)
    return out


def find_window(keywords):
    """keywords 우선순위대로 제목에 포함된 창을 찾음. 없으면 None."""
    wins = _list_windows()
    for kw in keywords:
        for hwnd, title in wins:
            if title.startswith("Gesture Controller"):
                continue
            if kw.lower() in title.lower():
                return hwnd
    return None


def foreground_window():
    return user32.GetForegroundWindow()


def focus_window(hwnd):
    """다른 프로세스 창을 앞으로 (Alt키 꼼수 없이 AttachThreadInput 방식)."""
    if user32.IsIconic(hwnd):
        user32.ShowWindow(hwnd, SW_RESTORE)
    fg = user32.GetForegroundWindow()
    tid_fg = user32.GetWindowThreadProcessId(fg, None)
    tid_me = kernel32.GetCurrentThreadId()
    attached = False
    if tid_fg and tid_fg != tid_me:
        attached = bool(user32.AttachThreadInput(tid_me, tid_fg, True))
    user32.SetForegroundWindow(hwnd)
    if attached:
        user32.AttachThreadInput(tid_me, tid_fg, False)