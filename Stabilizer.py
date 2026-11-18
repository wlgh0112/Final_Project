"""프레임 단위 오인식을 걸러내고, 이산 동작은 1회만 발동되게 한다."""
import time
from collections import deque
from typing import Optional, Tuple

import config


class GestureStabilizer:
    def __init__(self, confirm_frames=config.CONFIRM_FRAMES, cooldown=config.COOLDOWN_SEC):
        self.history = deque(maxlen=confirm_frames)
        self.cooldown = cooldown
        self.stable: Optional[str] = None
        self.last_fire = 0.0

    @property
    def progress(self) -> float:
        """현재 라벨이 연속으로 몇 프레임 유지됐는지 (0.0 ~ 1.0). 상태창 진행바용."""
        if not self.history or self.history[-1] is None:
            return 0.0
        n = 0
        for lab in reversed(self.history):
            if lab != self.history[-1]:
                break
            n += 1
        return n / self.history.maxlen

    def update(self, label: Optional[str]) -> Tuple[Optional[str], bool]:
        """
        returns (확정된 라벨 or None, 이번 프레임에 새로 확정된 순간인지)
        이산 동작은 'is_new and 쿨다운 경과'일 때만 실행하면 된다.
        """
        self.history.append(label)
        confirmed = None
        if len(self.history) == self.history.maxlen and len(set(self.history)) == 1:
            confirmed = self.history[0]

        is_new = False
        if confirmed is not None and confirmed != self.stable:
            now = time.time()
            if now - self.last_fire >= self.cooldown:
                is_new = True
                self.last_fire = now
        self.stable = confirmed
        return confirmed, is_new