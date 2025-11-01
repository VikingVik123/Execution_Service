from pydantic import BaseModel

class SignalSchema(BaseModel):
    """
    Schema for signal data.
    """
    symbol: str
    side: str
    type: str
    entry: float
    sl: float
    tp: float

class CloseSignalSchema(BaseModel):
    """
    Schema for close signal data.
    """
    symbol: str