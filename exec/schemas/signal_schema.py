from pydantic import BaseModel

class SignalSchema(BaseModel):
    """
    Schema for opening a position signal.
    """
    symbol: str
    side: str        # "buy" or "sell"
    entry: float
    sl: float
    tp: float
    margin: float = 30      # Optional, default 30 USDT
    leverage: int = 10      # Optional, default 10x

class CloseSignalSchema(BaseModel):
    """
    Schema for closing a position.
    """
    symbol: str
