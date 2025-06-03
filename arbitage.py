import ccxt
import time
import logging

# --- LOGGING SETUP ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('arbitrage.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# --- CONFIGURATION ---
symbol = 'BTC/USDT'
initial_funds = 500.0
trade_amount = 200.0
min_spread_percent = 0.005  # 0.5%
taker_fee = 0      # 0.04% typical fee

# --- MOCK STATE ---
funds = initial_funds
cumulative_profit = 0.0
trade_log = []
max_spread = 0

# --- EXCHANGES ---
binance = ccxt.binance()
kucoin = ccxt.kucoin()

logger.info(f"[START] Mock arbitrage bot running with ${initial_funds:.2f} USDT...\n")

# --- MAIN LOOP ---
try:
    while True:
        try:
            # --- FETCH LIVE PRICES ---
            price_binance = binance.fetch_ticker(symbol)['last']
            price_kucoin = kucoin.fetch_ticker(symbol)['last']

            logger.info(f"[PRICES] Binance: ${price_binance:.2f}, KuCoin: ${price_kucoin:.2f}")

            if price_binance > price_kucoin:
                spread = price_binance - price_kucoin
                spread_percent = (spread / price_kucoin) * 100
                logger.info(f"[SPREAD] {spread_percent:.4f}% | Spread: ${spread:.2f}")

                # Track new max spread
                if spread_percent > max_spread:
                    max_spread = spread_percent
                    logger.info(f"📈 New max spread: {max_spread:.4f}%")

                # --- ARBITRAGE CONDITIONS MET ---
                if spread_percent >= min_spread_percent and funds >= trade_amount:
                    btc_bought = trade_amount / price_kucoin
                    sell_value = btc_bought * price_binance

                    buy_fee = trade_amount * taker_fee
                    sell_fee = sell_value * taker_fee
                    net_profit = sell_value - trade_amount - buy_fee - sell_fee

                    logger.info(f"💡 Evaluated net profit: ${net_profit:.4f} | Buy fee: ${buy_fee:.2f} | Sell fee: ${sell_fee:.2f}")

                    if net_profit > 0:
                        # Simulate profit
                        funds += net_profit
                        cumulative_profit += net_profit

                        trade_log.append({
                            'buy_price': price_kucoin,
                            'sell_price': price_binance,
                            'btc': round(btc_bought, 6),
                            'profit': round(net_profit, 2)
                        })

                        logger.info(f"✅ TRADE EXECUTED | Profit: ${net_profit:.2f} | New Balance: ${funds:.2f}")
                    else:
                        logger.info(f"❌ Skipped - Net profit too low: ${net_profit:.4f}")
                else:
                    logger.debug("⏳ No trade - Spread not large enough or funds too low")
            else:
                logger.debug("↔️ No opportunity - Binance price not higher than KuCoin")

            time.sleep(10)

        except Exception as e:
            logger.error(f"🔥 ERROR: {str(e)}", exc_info=True)
            time.sleep(5)

except KeyboardInterrupt:
    logger.info("🛑 Bot stopped by user")
    print("\n\n[FINAL REPORT]")
    logger.info(f"Final Balance: ${funds:.2f}")
    logger.info(f"Total Trades Executed: {len(trade_log)}")

    for i, trade in enumerate(trade_log[-5:], 1):
        print(f"#{i}: Bought at ${trade['buy_price']:.2f} | Sold at ${trade['sell_price']:.2f} | Profit: ${trade['profit']:.2f}")
