"""카메라 좌표 -> 화면 좌표 변환 + 떨림 제거(EMA)."""
import config


class CoordMapper:
    def __init__(self, frame_w, frame_h, screen_w, screen_h):
        self.fw, self.fh = frame_w, frame_h
        self.sw, self.sh = screen_w, screen_h
        self.sx = self.sy = None

    def reset(self):
        self.sx = self.sy = None

    def map(self, cx, cy):
        m = config.ROI_MARGIN
        nx = (cx / self.fw - m) / (1 - 2 * m)
        ny = (cy / self.fh - m) / (1 - 2 * m)
        nx, ny = min(max(nx, 0.0), 1.0), min(max(ny, 0.0), 1.0)
        x, y = nx * self.sw, ny * self.sh

        a = config.SMOOTHING_ALPHA
        if self.sx is None:
            self.sx, self.sy = x, y
        else:
            self.sx += a * (x - self.sx)
            self.sy += a * (y - self.sy)
        return int(self.sx), int(self.sy)