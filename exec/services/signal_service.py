import os
import sys
import time
import math
import ccxt
from dotenv import load_dotenv

load_dotenv()

class SignalService:
    def __init__(self):
        self.API_KEY = os.getenv("API_KEY")
        self.API_SECRET = os.getenv("API_SECRET")

        self.exchange = ccxt.bybit({
            "apiKey": (self.API_KEY or "").strip(),
            "secret": (self.API_SECRET or "").strip(),
            "options": {"defaultType": "linear"},
            "enableRateLimit": True,
        })

        try:
            self.exchange.load_markets()
        except Exception as e:
            print(f"CRITICAL ERROR loading markets: {e}", file=sys.stderr)

    # -----------------------------
    # Set leverage
    # -----------------------------
    def set_leverage(self, symbol: str, leverage: int = 10):
        symbol_ccxt = symbol.upper()
        try:
            self.exchange.privatePostV5PositionSetLeverage({
                "category": "linear",
                "symbol": symbol_ccxt,
                "buyLeverage": str(leverage),
                "sellLeverage": str(leverage),
            })
            print(f"✅ Leverage set to {leverage}x for {symbol_ccxt}")
        except Exception as e:
            # Bybit returns an error when leverage is already set — safe to continue
            print(f"❌ Failed to set leverage (can be ignored if already set): {e}")

    # -----------------------------
    # Place limit order with TP/SL
    # -----------------------------
    def place_order(self, symbol: str, side: str, entry: float,
                    tp: float, sl: float, margin: float = 30, leverage: int = 10):
        """
        - Places a Limit order via Bybit v5 (ccxt privatePost wrapper)
        - Immediately creates reduce-only TP and SL conditional orders (tpslOrder)
          so they are attached to the order/position without waiting for fill.
        - Returns the main order id (or raw response) on success, or None on failure.
        """

        # Basic validation
        if not symbol or not side:
            print("❌ symbol and side are required.")
            return None

        symbol_ccxt = symbol.upper()  # e.g., "DOGEUSDT"
        if side.lower() not in ("buy", "sell"):
            print(f"❌ Invalid side '{side}'. Use 'buy' or 'sell'.")
            return None
        # Bybit v5 expects "Buy" or "Sell" in the v5 order/create payload
        side_bybit = "Buy" if side.lower() == "buy" else "Sell"
        close_side = "Sell" if side_bybit == "Buy" else "Buy"  # side for TP/SL orders

        # 1️⃣ Set leverage (best-effort)
        self.set_leverage(symbol_ccxt, leverage)

        # 2️⃣ Prevent opening duplicate positions
        try:
            positions = self.exchange.fetch_positions([symbol_ccxt])
        except Exception as e:
            print(f"❌ Failed to fetch positions: {e}")
            return None

        open_position = next((p for p in positions if abs(float(p.get("contracts", 0))) > 0), None)
        if open_position:
            print(f"⚠️ Open position exists. Skipping order for {symbol_ccxt}.")
            return None

        # 3️⃣ Compute qty from margin * leverage and round down to integer contracts
        notional = float(margin) * int(leverage)   # USDT notional
        if entry <= 0:
            print("❌ Invalid entry price.")
            return None

        raw_amount = notional / float(entry)       # theoretical base-asset qty (e.g., DOGE)
        # Floor to integer qty for small-alts on Bybit (adjust if instrument supports fraction)
        qty = math.floor(raw_amount)
        if qty <= 0:
            print(f"❌ Computed qty is zero or negative (raw={raw_amount}). Increase margin or adjust entry.")
            return None

        print(f"📌 Placing {side_bybit} Limit order: {qty} {symbol_ccxt.replace('USDT','')} @ {entry} (notional ≈ {notional} USDT)")

        # 4️⃣ Place main limit order via v5 order/create using CCXT private POST wrapper
        try:
            payload = {
                "category": "linear",
                "symbol": symbol_ccxt,
                "side": side_bybit,
                "orderType": "Limit",
                "qty": str(qty),
                "price": str(entry),
                "timeInForce": "GTC",
                "reduceOnly": False,
            }
            resp = self.exchange.privatePostV5OrderCreate(payload)
            # Typical successful response structure:
            # { "retCode":0, "retMsg":"OK", "result": {"orderId": "...", ... }, ... }
            order_id = None
            if isinstance(resp, dict):
                result = resp.get("result")
                if isinstance(result, dict):
                    order_id = result.get("orderId") or result.get("order_id") or result.get("orderLinkId")
            print(f"✅ Main order placed. Raw response: {resp}")
            if not order_id:
                # return raw response so caller can inspect
                return resp
        except Exception as e:
            print(f"❌ Failed to place main order: {e}")
            return None

        # 5️⃣ Create reduce-only TP and SL conditional orders (tpslOrder)
        # These use create_order so CCXT will format properly; include Bybit-specific params.
        try:
            # TAKE PROFIT
            tp_order = self.exchange.create_order(
                symbol=symbol_ccxt,
                type="limit",
                side=close_side,
                amount=qty,
                price=str(tp),
                params={
                    "category": "linear",
                    "reduceOnly": True,
                    "triggerDirection": 1 if side_bybit == "Buy" else 2,
                    "triggerPrice": str(tp),
                    "orderFilter": "tpslOrder",
                    "tpslOrderType": "tp",
                    # optional: "positionIdx": 0
                }
            )
            print(f"✅ TP set @ {tp} (raw: {tp_order})")
        except Exception as e:
            print(f"⚠️ Failed to place TP conditional order: {e}")

        try:
            # STOP LOSS
            sl_order = self.exchange.create_order(
                symbol=symbol_ccxt,
                type="limit",
                side=close_side,
                amount=qty,
                price=str(sl),
                params={
                    "category": "linear",
                    "reduceOnly": True,
                    "triggerDirection": 2 if side_bybit == "Buy" else 1,
                    "triggerPrice": str(sl),
                    "orderFilter": "tpslOrder",
                    "tpslOrderType": "sl",
                    # optional: "positionIdx": 0
                }
            )
            print(f"✅ SL set @ {sl} (raw: {sl_order})")
        except Exception as e:
            print(f"⚠️ Failed to place SL conditional order: {e}")

        # Return the main order id
        return order_id

    # -----------------------------
    # Close any open position
    # -----------------------------
    def close_position(self, symbol: str):
        symbol_ccxt = symbol.upper()
        try:
            positions = self.exchange.fetch_positions([symbol_ccxt])
            pos = next((p for p in positions if abs(p["contracts"]) > 0), None)
            if not pos:
                print("No open position.")
                return None

            size = abs(pos["contracts"])
            side = pos["side"]
            close_side = "sell" if side == "long" else "buy"

            close_order = self.exchange.create_order(
                symbol=symbol_ccxt,
                type="market",
                side=close_side,
                amount=size,
                params={"reduceOnly": True}
            )
            print(f"✅ Closed {side.upper()} size={size}. ID={close_order.get('id') or close_order}")
            return close_order.get("id") if isinstance(close_order, dict) and close_order.get("id") else close_order

        except Exception as e:
            print(f"❌ Failed to close position: {e}")
            return None
