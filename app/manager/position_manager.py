from datetime import datetime
from typing import Dict, Optional

from models.position import Position, PositionSide


class PositionManager:
    def __init__(self):
        self.positions: Dict[str, Position] = {}
        self.position_updated = None
        
    def open_position(self, symbol: str, side: PositionSide, size: float, entry_price: float, stop_loss: Optional[float] = None):
        position = Position(
            symbol=symbol,
            side=side,
            size=size,
            entry_price=entry_price,
            stop_loss=stop_loss,
            entry_time=datetime.now()
        )
        self.positions[symbol] = position
        if self.position_updated:
            self.position_updated.emit(position)
        return position
    
    def close_position(self, symbol: str):
        if symbol in self.positions:
            position = self.positions.pop(symbol)
            if self.position_updated:
                self.position_updated.emit(None)
            return position
        return None
    
    def update_stop_loss(self, symbol: str, new_stop_loss: float):
        if symbol in self.positions:
            self.positions[symbol].stop_loss = new_stop_loss
            if self.position_updated:
                self.position_updated.emit(self.positions[symbol])
    
    def update_current_prices(self, symbol: str, price: float):
        if symbol in self.positions:
            self.positions[symbol].update_pnl(price)
            if self.position_updated:
                self.position_updated.emit(self.positions[symbol])
    
    def get_position(self, symbol: str) -> Optional[Position]:
        return self.positions.get(symbol)
    
    def has_position(self, symbol: str) -> bool:
        return symbol in self.positions