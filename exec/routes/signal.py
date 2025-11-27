from fastapi import APIRouter, HTTPException
from services.signal_service import SignalService
from schemas.signal_schema import SignalSchema, CloseSignalSchema
import ccxt  # Required for exception handling

router = APIRouter()
signal_service = SignalService()


@router.post("/signals")
async def create_signal(signal: SignalSchema):
    """
    Place a limit order with TP/SL via SignalService.
    """
    try:
        order_id = signal_service.place_order(
            symbol=signal.symbol,
            side=signal.side,
            entry=signal.entry,
            tp=signal.tp,
            sl=signal.sl,
            margin=signal.margin,
            leverage=signal.leverage
        )
        if not order_id:
            raise HTTPException(status_code=400, detail="Order could not be placed (check existing positions or parameters).")
        return {"order_id": order_id}

    except ccxt.InsufficientFunds as e:
        raise HTTPException(status_code=400, detail=f"Insufficient Funds: {e}")

    except ccxt.InvalidOrder as e:
        raise HTTPException(status_code=400, detail=f"Invalid Order: {e}")

    except ccxt.NetworkError as e:
        raise HTTPException(status_code=504, detail=f"Network Error: {e}")

    except ccxt.ExchangeError as e:
        raise HTTPException(status_code=400, detail=f"Bybit Exchange Error: {e}")

    except Exception as e:
        print(f"--- Unexpected internal error: {repr(e)} ---")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {repr(e)}")


@router.post("/close")
async def close_position(signal: CloseSignalSchema):
    """
    Close any open position for a given symbol.
    """
    try:
        result = signal_service.close_position(symbol=signal.symbol)
        if not result:
            raise HTTPException(status_code=400, detail="No open position to close.")
        return {"close_order_id": result}

    except ccxt.NetworkError as e:
        raise HTTPException(status_code=504, detail=f"Network Error: {e}")

    except ccxt.ExchangeError as e:
        raise HTTPException(status_code=400, detail=f"Bybit Exchange Error: {e}")

    except Exception as e:
        print(f"--- Unexpected internal error: {repr(e)} ---")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {repr(e)}")
