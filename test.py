import ccxt


class SampExec:
    def __init__(self):
        self.exchange = ccxt.bybit({
            "apiKey": "nDgHWYiLi66wsoCs4V",
            "secret": "cTHqwR68tLRdmpoMWpIAdvb8mrZJMJLUwixI",
            "options": {
                "defaultType": "linear",
            },
            "urls": {
                    "api": {
                        "public": "https://api-testnet.bybit.com",
                        "private": "https://api-testnet.bybit.com",
                    }
                },
                #"verbose": True
        })
        self.exchange.load_markets()

    def place_order(self, symbol: str, side: str, type:str, entry: float, sl: float, tp: float):
        print("--- Received signal ---")
        print(f"Symbol: {symbol}, Side: {side}, Type: {type}, Entry: {entry}, SL: {sl}, TP: {tp}"),
        symbol_ccxt = symbol.upper()
        amount_float = 1 / entry

        order_params = {
            "symbol": symbol_ccxt,
            "type": type,
            "side": side,
            "amount": amount_float, # Pass the float directly
            "params": {}
        }

        try:
            order = self.exchange.create_order(**order_params)
            #print(f"Order placed successfully: {order}")
            order_id = order['id']          # <-- Bybit orderId
            print({order_id})
            return order_id 
        except Exception as e:
            print(f"Error placing order: {e}")

    def balance(self):
        balance = self.exchange.fetch_balance(
            params = {"accountType": "UNIFIED"}
        )
        usdt_balance = balance.get('USDT', {})
        return usdt_balance
    
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


if __name__ == "__main__":
    samp_exec = SampExec()
    samp_exec.place_order("DOGEUSDT", "Sell", "Market", 0.16240, 0.15240, 0.17240)
    #balance = samp_exec.balance()
    #print(balance)
    #samp_exec.close_position("DOGEUSDT")