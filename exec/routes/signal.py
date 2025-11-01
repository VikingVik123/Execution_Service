from fastapi import APIRouter, HTTPException
from services.signal_service import SignalService
from schemas.signal_schema import SignalSchema, CloseSignalSchema
import ccxt  # <-- Import ccxt here

router = APIRouter()
signal_service = SignalService()

@router.post("/signals")
async def create_signal(signal: SignalSchema):
    # --- ADD THIS ERROR HANDLING ---
    try:
        order = signal_service.place_order(
            symbol=signal.symbol,
            side=signal.side,
            type=signal.type,
            entry=signal.entry,
            tp=signal.tp,
            sl=signal.sl
        )
        return order
    
    except ccxt.InsufficientFunds as e:
        raise HTTPException(status_code=400, detail=f"Insufficient Funds: {e}")

    except ccxt.InvalidOrder as e:
        # This catches "order size too small", "invalid symbol", etc.
        raise HTTPException(status_code=400, detail=f"Invalid Order: {e}")

    except ccxt.NetworkError as e:
        raise HTTPException(status_code=504, detail=f"Network Error: {e}")
    
    except ccxt.ExchangeError as e:
        # This is the most common one!
        raise HTTPException(status_code=400, detail=f"Bybit Exchange Error: {e}")
    

    except Exception as e:
        # Catch any other error (like the TypeError or other bugs)
        print(f"--- An unexpected internal error occurred: {repr(e)} ---")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {repr(e)}")
    

@router.post("/close")
async def close_position(signal: CloseSignalSchema):
    try:
        result = signal_service.close_position(symbol=signal.symbol)
        return result

    except ccxt.NetworkError as e:
        raise HTTPException(status_code=504, detail=f"Network Error: {e}")
    
    except ccxt.ExchangeError as e:
        raise HTTPException(status_code=400, detail=f"Bybit Exchange Error: {e}")

    except Exception as e:
        print(f"--- An unexpected internal error occurred: {repr(e)} ---")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {repr(e)}")
