"""화면 전체를 덮는 투명 오버레이(클릭 통과): 레이저 포인터, 판서.
동작 표시는 panel.py의 작은 창이 담당."""
import queue
import threading
import tkinter as tk

import config
from panel import ActionPanel
from winutil import (set_ex_style, WS_EX_LAYERED, WS_EX_TRANSPARENT,
                     WS_EX_NOACTIVATE, WS_EX_TOOLWINDOW)

TRANSPARENT = "#010101"
FONT = "Malgun Gothic"


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
        r.update_idletasks()
        set_ex_style(r, WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW)

        self.panel = ActionPanel(r)      # 오버레이 위에 뜨는 작은 동작 표시 창

    # ---------- 포인터 / 판서 ----------
    def _show_pointer(self, x, y, color):
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
            edge = c.create_line(x0, y0, x, y, fill="white", width=w + 4,
                                 capstyle="round", tags="stroke")
            c.tag_lower(edge)
            c.create_line(x0, y0, x, y, fill=config.PEN_COLOR, width=w,
                          capstyle="round", tags="stroke")
        self.last_pen = (x, y)
        self._show_pointer(x, y, config.PEN_COLOR)

    # ---------- (선택) 화면 상단 큰 팝업: config.SHOW_TOAST ----------
    def _toast(self, text, color):
        c = self.canvas
        c.delete("toast")
        t = c.create_text(self.sw // 2, 110, text=text, fill="white",
                          font=(FONT, -48, "bold"), tags="toast")
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
                    self.panel.flash(*args)
                    if config.SHOW_TOAST:
                        self._toast(*args)
                elif ev == "status":
                    self.panel.set_status(*args)
        except queue.Empty:
            pass
        self.canvas.tag_raise("pointer")
        self.canvas.tag_raise("toast")
        self.root.after(10, self._poll)

    def run(self):
        self.root.after(10, self._poll)
        self.root.mainloop()