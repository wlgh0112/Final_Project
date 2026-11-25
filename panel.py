
"""화면 구석의 동작 표시 창.
- 대기 모드: 작고 반투명 (슬라이드를 덜 가림) - 손 인식 상태만 한 줄로 표시
- 동작 모드: 동작이 실행되면 커지고 불투명해지면서 동작 색 배경 + 큰 글씨로 강조
- 오른쪽 아래 모서리를 기준으로 커지고 줄어듦. 마우스로 끌어서 위치 이동 가능,
  클릭해도 PPT 포커스를 뺏지 않음."""
import time
import tkinter as tk

import config
from winutil import set_ex_style, WS_EX_NOACTIVATE, WS_EX_TOOLWINDOW

FONT = "Malgun Gothic"
DARK = "#111827"
DOT_NONE, DOT_CHECK, DOT_HOLD = "#6b7280", "#f59e0b", "#60a5fa"


def px(size, bold=True):
    return (FONT, -size, "bold") if bold else (FONT, -size)


class ActionPanel:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.EW, self.EH = config.PANEL_W, config.PANEL_H
        self.CW, self.CH = config.PANEL_COMPACT_W, config.PANEL_COMPACT_H

        w = self.win = tk.Toplevel(root)
        w.overrideredirect(True)
        w.attributes("-topmost", True)
        w.attributes("-alpha", config.PANEL_IDLE_ALPHA)
        sw, sh = w.winfo_screenwidth(), w.winfo_screenheight()
        self.x, self.y = sw - 40 - self.CW, sh - 110 - self.CH
        w.geometry(f"{self.CW}x{self.CH}+{self.x}+{self.y}")

        self.c = tk.Canvas(w, width=self.CW, height=self.CH, highlightthickness=0, bg=DARK)
        self.c.pack()
        self.c.bind("<ButtonPress-1>", self._drag_start)
        self.c.bind("<B1-Motion>", self._drag_move)
        w.update_idletasks()
        set_ex_style(w, WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW)

        self.cur_w, self.cur_h, self.cur_a = self.CW, self.CH, config.PANEL_IDLE_ALPHA
        self.mode = "idle"
        self.state = (None, None, 0.0)
        self.flash_text, self.flash_color, self.flash_until = "", config.IDLE_COLOR, 0.0
        self.view = self._view()
        self._key = None
        self._anim_job = None
        self._off = (0, 0)
        self._render()

    # ----- 외부에서 호출 -----
    def set_status(self, raw_label, action, progress):
        self.state = (raw_label, action, progress)
        self._refresh()

    def flash(self, text, color):
        """동작 실행 순간 강조."""
        ms = config.PANEL_FLASH_MS
        self.flash_text, self.flash_color = text, color
        self.flash_until = time.time() + ms / 1000
        self._refresh()
        self.root.after(ms + 30, self._refresh)

    # ----- 상태 -> 화면 내용 -----
    def _view(self):
        """(모드, 제목, 배경색, 부제, 진행률, 글자크기, 점색)"""
        raw, action, progress = self.state
        if time.time() < self.flash_until:
            return ("active", self.flash_text, self.flash_color, "동작 실행!", 1.0, 34, None)
        if action in config.CONTINUOUS_ACTIONS:
            return ("active", config.ACTION_LABELS[action], config.ACTION_COLORS[action],
                    f"인식: {raw}" if raw else "", 1.0, 31, None)
        if raw:
            checking = progress < 1.0
            return ("idle", "확인 중..." if checking else "대기 중", DARK, f"인식: {raw}",
                    progress, 20, DOT_CHECK if checking else DOT_HOLD)
        return ("idle", "손 인식 안 됨", DARK, "카메라에 손을 보여주세요", 0.0, 20, DOT_NONE)

    def _refresh(self):
        view = self._view()
        key = view[:4] + (round(view[4] * 10),)
        if key == self._key:
            return
        self._key = key
        self.view = view
        if view[0] != self.mode:
            self.mode = view[0]
            self._animate()
        else:
            self._render()

    # ----- 크기/투명도 애니메이션 (오른쪽 아래 모서리 고정) -----
    def _animate(self):
        if self._anim_job:
            self.root.after_cancel(self._anim_job)
        if self.mode == "active":
            tw, th, ta = self.EW, self.EH, config.PANEL_ACTIVE_ALPHA
        else:
            tw, th, ta = self.CW, self.CH, config.PANEL_IDLE_ALPHA
        sw, sh, sa = self.cur_w, self.cur_h, self.cur_a
        steps = 6
        dt = max(config.PANEL_ANIM_MS // steps, 10)

        def step(i):
            t = i / steps
            self._resize(int(sw + (tw - sw) * t), int(sh + (th - sh) * t), sa + (ta - sa) * t)
            self._render()
            self._anim_job = self.root.after(dt, lambda: step(i + 1)) if i < steps else None

        step(1)

    def _resize(self, w, h, a):
        right, bottom = self.x + self.cur_w, self.y + self.cur_h
        self.x, self.y = right - w, bottom - h
        self.win.geometry(f"{w}x{h}+{self.x}+{self.y}")
        self.c.config(width=w, height=h)
        self.win.attributes("-alpha", a)
        self.cur_w, self.cur_h, self.cur_a = w, h, a

    # ----- 그리기 -----
    def _render(self):
        mode, title, bg, sub, progress, size, dot = self.view
        c, W, H = self.c, self.cur_w, self.cur_h
        c.delete("all")
        c.create_rectangle(0, 0, W, H, fill=bg, outline="white", width=3 if mode == "active" else 2)

        if mode == "active":
            c.create_text(14, 10, text="GESTURE CONTROL", anchor="nw", fill="#d1d5db", font=px(12))
            while True:
                t = c.create_text(W // 2, H // 2 - 8, text=title, fill="white", font=px(size))
                x1, _, x2, _ = c.bbox(t)
                if x2 - x1 <= W - 30 or size <= 14:
                    break
                c.delete(t)
                size -= 2
            c.create_text(W // 2, H - 34, text=sub, fill="#f3f4f6", font=px(15, bold=False))
            bar_y, bar_fill = H - 16, "white"
        else:
            c.create_oval(14, H // 2 - 8, 30, H // 2 + 8, fill=dot, outline="")
            c.create_text(42, H // 2 - 9, text=title, anchor="w", fill="white", font=px(size))
            c.create_text(42, H // 2 + 14, text=sub, anchor="w", fill="#e5e7eb", font=px(13, bold=False))
            bar_y, bar_fill = H - 9, dot

        c.create_rectangle(14, bar_y, W - 14, bar_y + 5, fill="#374151", outline="")
        if progress > 0:
            c.create_rectangle(14, bar_y, 14 + (W - 28) * progress, bar_y + 5, fill=bar_fill, outline="")

    # ----- 드래그로 이동 -----
    def _drag_start(self, e):
        self._off = (e.x_root - self.x, e.y_root - self.y)

    def _drag_move(self, e):
        self.x, self.y = e.x_root - self._off[0], e.y_root - self._off[1]
        self.win.geometry(f"+{self.x}+{self.y}")
