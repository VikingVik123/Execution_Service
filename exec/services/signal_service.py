import ccxt
import os
import sys
import time # Import time for the fetch_order delay
from dotenv import load_dotenv

load_dotenv()

class SignalService:
# ... existing __init__ method ...
    def __init__(self):
        # Load keys from environment
        self.API_TESTNET_KEY = os.getenv("API_TESTNET_KEY")
        self.API_TESTNET_SECRET = os.getenv("API_TESTNET_SECRET")

        # --- SANITY CHECK ---
        if not self.API_TESTNET_KEY or not self.API_TESTNET_SECRET:
            print("CRITICAL ERROR: API keys are missing from environment!", file=sys.stderr)
            raise ValueError("API_TESTNET_KEY or API_TESTNET_SECRET not found.")
        # ---------------------------
        print("--- Loaded API Key ---")  # Debug print
        print(f"Key: {self.API_TESTNET_KEY[:4]}...{self.API_TESTNET_KEY[-4:]}")

        # --- THIS IS THE CORRECTED CONFIG ---
        self.exchange = ccxt.bybit(
            {
                "apiKey": self.API_TESTNET_KEY.strip(),
                "secret": self.API_TESTNET_SECRET.strip(),
                
                "options": {
                    "defaultType": "linear" # Keep this for V5 API
                },
                
                # --- MANUALLY FORCE THE TESTNET URLS (Correct Format) ---
                "urls": {
                    "api": {
                        "public": "https://api-testnet.bybit.com",
                        "private": "https://api-testnet.bybit.com",
                    }
                },
                "verbose": True # Keep this for debugging
            }
        )
        print("--- CCXT Initialized Correctly for Testnet ---")

    def place_order(self, symbol: str, side: str, type:str, entry: float):
        """
        Place a FUTURES order and then fetch the full order details.
        """
        print(f"--- Received signal: symbol={symbol}, side={side}, type={type}, entry={entry}")

        # Standardize symbol for CCXT (it prefers slashes)
        if "/" not in symbol and "USDT" in symbol.upper():
            symbol_ccxt = symbol.upper().replace("USDT", "") + "/USDT"
        else:
            symbol_ccxt = symbol.upper()
        
        type_ccxt = type.lower().title() # 'market' -> 'Market'
        side_ccxt = side.lower().title() # 'buy' -> 'Buy'

        # 10 USDT notional value
        amount_float = 1 / entry 

        # --- FIX: "Qty invalid" (10001) ---
        # Bybit's API requires qty to be a STRING formatted to the
        # correct precision (qtyStep). For DOGEUSDT, the step is 1.
        # We must round to a whole number (using int()) and send as a string.
        
        # We use int() to floor the amount (e.g., 62.31 -> 62)
        amount_string = str(int(amount_float))
        
        print(f"--- Calculated amount (float): {amount_float}")
        print(f"--- Rounded amount to string (qtyStep=1): {amount_string}")
        # --- END FIX ---

        order_params = {
            "symbol": symbol_ccxt,
            "type": type_ccxt,
            "side": side_ccxt,
            "amount": amount_string, # <-- Use the formatted string
            # --- THIS IS THE FIX ---
            # We MUST specify the category for Unified Trading
            "params": {
                "category": "linear"  # 'linear' = USDT-M Futures
            }
        }

        if type_ccxt == 'Limit':
            order_params['price'] = entry

        # --- Set Leverage ---
        try:
            print(f"--- Setting leverage to 1x for {symbol_ccxt} (linear)")
            # Set leverage for the linear market
            self.exchange.set_leverage(2, symbol_ccxt,
                                       {"category": "linear",
                                       "buyLeverage": "1",
                                       "sellLeverage": "1",
                                       "positionIdx": 0,},)
            print(f"--- Set leverage complete.")
        except Exception as le:
            print(f"--- Warning: Could not set leverage (may be already set): {le}") 

        # --- 1. Create the order ---
        print(f"--- Attempting to place order with params: {order_params}")
        order_creation_response = self.exchange.create_order(**order_params)
        
        print("--- Order Created Successfully! (Minimal Response) ---")
        print(f"Creation Response: {order_creation_response}")
        
        order_id = order_creation_response['id']
        
        # --- 2. Wait for exchange to process the fill ---
        print("Waiting 1 second for order to populate...")
        time.sleep(1) # Wait 1 second
        
        # --- 3. Fetch the full order details ---
        print(f"Fetching full order details for ID: {order_id}")
        
        # We must also tell fetch_order the category!
        fetch_params = {"category": "linear"}
        fetched_order = self.exchange.fetchOpenOrder(order_id, symbol_ccxt, fetch_params)
        
        print("--- Successfully Fetched Full Order ---")
        print(fetched_order) # This will have status, filled, etc.
        
        return fetched_order
    
    def close_tp(self, order_id: str, symbol: str):
        """
        Close the position once take profit is hit.
        """