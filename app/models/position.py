from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional

class PositionSide(Enum):
    LONG = "LONG"
    SHORT = "SHORT"

@dataclass
class Position:
    symbol: str
    side: PositionSide
    size: float
    entry_price: float
    stop_loss: Optional[float] = None
    current_price: Optional[float] = None
    unrealized_pnl: float = 0.0
    entry_time: Optional[datetime] = None
    
    def update_pnl(self, current_price: float):
        self.current_price = current_price
        if self.side == PositionSide.LONG:
            self.unrealized_pnl = (current_price - self.entry_price) * self.size
        else:
            self.unrealized_pnl = (self.entry_price - current_price) * self.size