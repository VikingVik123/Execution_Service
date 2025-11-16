import ccxt
import os
import sys
import time # Import time for the fetch_order delay
from dotenv import load_dotenv

load_dotenv()

class SignalService:
    def __init__(self):
        # You must create a .env file with these new variable names
        self.API_KEY = os.getenv("API_KEY")
        self.API_SECRET = os.getenv("API_SECRET")

        print(f"Key: {self.API_KEY[:4]}...{self.API_KEY[-4:]}")
        # --- THIS IS THE BYBIT CONFIG ---
        self.exchange = ccxt.bybit(
            {
                "apiKey": self.API_KEY.strip(),
                "secret": self.API_SECRET.strip(),
                "options": {
                    # This tells ccxt to use Futures (e.g., USDT-M)
                    "defaultType": "linear", 
                },
                
                #"urls": {
                #    "api": {
                #        "public": "https://api-testnet.bybit.com",
                #        "private": "https://api-testnet.bybit.com",
                #    }
                #},
                "enableRateLimit": True,
            }
        )

        try:
            # Load markets to get symbol precision for amount
            self.exchange.load_markets()
        except Exception as e:
            print(f"CRITICAL ERROR: Failed to load markets: {e}", file=sys.stderr)

    # --- MODIFIED to accept sl and tp ---
    def place_order(self, symbol: str, side: str, type:str, entry: float, sl: float, tp: float):
        """
        Place a FUTURES order on Bybit and then fetch the full order details.
        """
        symbol_ccxt = symbol.upper()
        
        type_ccxt = type.lower().title() # 'market' -> 'Market'
        side_ccxt = side.lower().title() # 'buy' -> 'Buy'
        positions = self.exchange.fetch_positions([symbol_ccxt])
        open_position = next(
            (
                pos for pos in positions
                if float(pos.get("contracts", 0)) > 0 or abs(float(pos.get("positionAmt", 0))) > 0
            ),
            None
        )

        if open_position:
            print(f"⚠️ Skipping order: There is already an open position on {symbol_ccxt}")
            return None

        amount_float = 4 / entry 
        order_params = {
            "symbol": symbol_ccxt,
            "type": type_ccxt,
            "side": side_ccxt,
            "amount": amount_float, # Pass the float directly
            "params": {} # Empty params, no 'category' needed
        }

        # --- 1. Create the order ---
        order_creation_response = self.exchange.create_order(**order_params)        
        order_id = order_creation_response['id']
        print(order_id)
        return order_id

    def close_position(self, symbol: str):
        symbol_ccxt = symbol.upper()
        try:
            positions = self.exchange.fetch_positions([symbol_ccxt])
            #print(positions)
            pos = None
            for p in positions:
                if p['contracts'] != 0 and p['symbol'].startswith(f"{symbol_ccxt.replace('USDT', '/USDT')}:"):
                    pos = p
                    break

            if not pos:
                print(f"No open position for {symbol_ccxt}")
                return None
            
            size   = abs(pos['contracts'])          # e.g. 6.0
            side   = pos['side']                    # 'long' or 'short'
            close_side = 'sell' if side == 'long' else 'buy'

            print(f"Closing {side.upper()} position: {size} contracts @ market")
            # 2. Place reduce-only market order
            close_order = self.exchange.create_order(
                symbol=symbol_ccxt,
                type='market',
                side=close_side,
                amount=size,
                params={'reduceOnly': True}
            )
            close_id = close_order['id']
            print(f"Position closed → Order ID: {close_id}")
            return close_id
        except Exception as e:
            print(f"Error fetching positions: {e}")
            return None