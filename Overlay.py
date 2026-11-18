"""화면 위에 투명하게 떠서 레이저 포인터 / 판서 / 상태창 / 안내 팝업을 그리는 오버레이 (Windows 전용).
클릭 통과 + 포커스 안 뺏기 설정 -> 발표 프로그램의 키 입력이 방해받지 않음."""
import ctypes
import queue
import threading
import tkinter as tk

import config

TRANSPARENT = "#010101"
FONT = "Malgun Gothic"
GWL_EXSTYLE = -20
WS_EX_LAYERED, WS_EX_TRANSPARENT = 0x80000, 0x20
WS_EX_NOACTIVATE, WS_EX_TOOLWINDOW = 0x08000000, 0x80


def px(size, bold=True):
    """음수 크기 = 픽셀 단위 (고DPI에서도 글자가 작아지지 않음)."""
    return (FONT, -size, "bold") if bold else (FONT, -size)


class Overlay:
    def __init__(self, events: "queue.Queue", stop: threading.Event):
        self.q, self.stop = events, stop
        self.root = tk.Tk()
        self.sw, self.sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()

        r = self.root
        r.overrideredirect(True)
        r.geometry(f"{self.sw}x{self.sh}+0+0")
        r.attributes("-topmost", True)
        r.attributes("-transparentcolor", TRANSPARENT)
        r.config(bg=TRANSPARENT)

        self.canvas = tk.Canvas(r, bg=TRANSPARENT, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self.pointer_ids = None
        self.last_pen = None
        self._toast_job = None
        self._hud_key = None
        r.update_idletasks()
        self._make_click_through()
        self._hud(None, None, 0.0)

    def _make_click_through(self):
        user32 = ctypes.windll.user32
        hwnd = user32.GetParent(self.root.winfo_id()) or self.root.winfo_id()
        style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        user32.SetWindowLongW(
            hwnd, GWL_EXSTYLE,
            style | WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW,
        )

    # ---------- 포인터 / 판서 ----------
    def _show_pointer(self, x, y, color):
        """흰 테두리 + 색 원: 어떤 슬라이드 배경에서도 보임."""
        R = config.POINTER_RADIUS
        c = self.canvas
        if self.pointer_ids is None:
            outer = c.create_oval(0, 0, 0, 0, fill="white", outline="", tags="pointer")
            inner = c.create_oval(0, 0, 0, 0, fill=color, outline="", tags="pointer")
            self.pointer_ids = (outer, inner)
        outer, inner = self.pointer_ids
        c.coords(outer, x - R - 5, y - R - 5, x + R + 5, y + R + 5)
        c.coords(inner, x - R, y - R, x + R, y + R)
        c.itemconfig(inner, fill=color)

    def _hide_pointer(self):
        self.canvas.delete("pointer")
        self.pointer_ids = None

    def _draw(self, x, y):
        c = self.canvas
        if self.last_pen is not None:
            x0, y0 = self.last_pen
            w = config.PEN_WIDTH
            # 흰 테두리 선은 맨 아래로 내려서 이전 획의 색을 덮지 않게 함
            edge = c.create_line(x0, y0, x, y, fill="white", width=w + 4,
                                 capstyle="round", tags="stroke")
            c.tag_lower(edge)
            c.create_line(x0, y0, x, y, fill=config.PEN_COLOR, width=w,
                          capstyle="round", tags="stroke")
        self.last_pen = (x, y)
        self._show_pointer(x, y, config.PEN_COLOR)

    # ---------- 하단 상태창 (항상 표시) ----------
    def _hud(self, raw_label, action, progress):
        key = (raw_label, action, round(progress * 10))
        if key == self._hud_key:
            return
        self._hud_key = key

        c = self.canvas
        c.delete("hud")
        W, H, M = 400, 104, 40
        x1, y1 = self.sw - W - M, self.sh - H - M - 40      # 작업표시줄 위
        x2, y2 = x1 + W, y1 + H
        color = config.ACTION_COLORS.get(action, config.IDLE_COLOR) if action else config.IDLE_COLOR

        if action:
            title = config.ACTION_LABELS.get(action, action)
        elif raw_label:
            title = "확인 중..."
        else:
            title = "손 인식 안 됨"
        sub = f"인식된 제스처: {raw_label}" if raw_label else "카메라에 손을 보여주세요"

        c.create_rectangle(x1, y1, x2, y2, fill="#111827", outline="white", width=2, tags="hud")
        c.create_rectangle(x1, y1, x1 + 16, y2, fill=color, outline="", tags="hud")
        c.create_text(x1 + 36, y1 + 14, text=title, anchor="nw", fill="white",
                      font=px(30), tags="hud")
        c.create_text(x1 + 36, y1 + 56, text=sub, anchor="nw", fill="#e5e7eb",
                      font=px(18, bold=False), tags="hud")
        bar_x1, bar_x2, bar_y = x1 + 36, x2 - 20, y2 - 18
        c.create_rectangle(bar_x1, bar_y, bar_x2, bar_y + 8, fill="#374151", outline="", tags="hud")
        if progress > 0:
            c.create_rectangle(bar_x1, bar_y, bar_x1 + (bar_x2 - bar_x1) * progress, bar_y + 8,
                               fill=color, outline="", tags="hud")

    # ---------- 상단 큰 안내 팝업 ----------
    def _toast(self, text, color):
        c = self.canvas
        c.delete("toast")
        t = c.create_text(self.sw // 2, 110, text=text, fill="white", font=px(48), tags="toast")
        x1, y1, x2, y2 = c.bbox(t)
        bg = c.create_rectangle(x1 - 40, y1 - 20, x2 + 40, y2 + 20, fill=color,
                                outline="white", width=4, tags="toast")
        c.tag_lower(bg, t)
        if self._toast_job:
            self.root.after_cancel(self._toast_job)
        self._toast_job = self.root.after(config.TOAST_MS, lambda: c.delete("toast"))

    # ---------- 이벤트 처리 ----------
    def _poll(self):
        if self.stop.is_set():
            self.root.destroy()
            return
        try:
            while True:
                ev, *args = self.q.get_nowait()
                if ev == "pointer":
                    self.last_pen = None
                    self._show_pointer(*args, config.ACTION_COLORS["pointer"])
                elif ev == "draw":
                    self._draw(*args)
                elif ev == "idle":
                    self.last_pen = None
                    self._hide_pointer()
                elif ev == "clear":
                    self.canvas.delete("stroke")
                elif ev == "toast":
                    self._toast(*args)
                elif ev == "status":
                    self._hud(*args)
        except queue.Empty:
            pass
        for tag in ("pointer", "hud", "toast"):      # 항상 판서 위에 보이게
            self.canvas.tag_raise(tag)
        self.root.after(10, self._poll)

    def run(self):
        self.root.after(10, self._poll)
        self.root.mainloop()