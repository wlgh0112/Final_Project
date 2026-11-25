"""카메라 미리보기 창 (Tk). 박스/인식 결과가 그려진 화면을 보여주고,
카메라/모델 문제가 있으면 그 이유를 글씨로 표시한다.
클릭해도 PPT 포커스를 뺏지 않으며, 창의 X 버튼을 누르면 프로그램이 종료된다."""
import base64
import tkinter as tk

import cv2

import config
from winutil import set_ex_style, WS_EX_NOACTIVATE


class Shared:
    """카메라 스레드 -> 미리보기 창으로 넘기는 값 (최신 프레임 / 안내 메시지)."""
    def __init__(self):
        self.frame = None
        self.message = "프로그램 시작 중..."


class PreviewWindow:
    def __init__(self, root: tk.Tk, stop, shared: Shared):
        self.root, self.stop, self.shared = root, stop, shared
        W, H = config.PREVIEW_W, config.PREVIEW_H

        w = self.win = tk.Toplevel(root)
        w.title("카메라 미리보기 (X: 종료)")
        w.attributes("-topmost", True)
        w.geometry(f"{W}x{H}+30+{w.winfo_screenheight() - H - 120}")
        w.resizable(False, False)
        w.protocol("WM_DELETE_WINDOW", stop.set)

        self.label = tk.Label(w, text=shared.message, bg="black", fg="white",
                              font=("Malgun Gothic", -17, "bold"),
                              wraplength=W - 30, justify="center")
        self.label.pack(fill="both", expand=True)
        w.update_idletasks()
        set_ex_style(w, WS_EX_NOACTIVATE)

        self._img = None
        self._last = None
        root.after(40, self._tick)

    def _tick(self):
        if self.stop.is_set():
            return
        frame = self.shared.frame
        if frame is None:
            self.label.config(image="", text=self.shared.message)
            self._last = None
        elif frame is not self._last:
            self._last = frame
            small = cv2.resize(frame, (config.PREVIEW_W, config.PREVIEW_H))
            ok, buf = cv2.imencode(".png", small)
            if ok:
                self._img = tk.PhotoImage(data=base64.b64encode(buf).decode("ascii"))
                self.label.config(image=self._img, text="")
        self.root.after(40, self._tick)