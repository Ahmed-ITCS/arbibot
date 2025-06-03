from flask import Flask, render_template, jsonify, request
from flask_sqlalchemy import SQLAlchemy
import threading
import time
import ccxt
import logging

# --- Initialize Flask App ---
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///trades.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- Database Models ---
class Trade(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    buy_exchange = db.Column(db.String(20))
    sell_exchange = db.Column(db.String(20))
    buy_price = db.Column(db.Float)
    sell_price = db.Column(db.Float)
    amount = db.Column(db.Float)
    profit = db.Column(db.Float)
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())

# --- Bot Configuration ---
class ArbitrageBot:
    def __init__(self):
        self.symbol = 'BTC/USDT'
        self.initial_funds = 500.0
        self.trade_amount = 200.0
        self.min_spread_percent = 0.005
        self.taker_fee = 0
        self.funds = self.initial_funds
        self.cumulative_profit = 0.0
        self.max_spread = 0.0
        self.running = False
        self.binance = ccxt.binance()
        self.kucoin = ccxt.kucoin()
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('arbitrage.log'),
                logging.StreamHandler()
            ]
        )

    def run(self):
        self.running = True
        self.logger.info(f"[START] Mock arbitrage bot running with ${self.initial_funds:.2f} USDT...")
        
        try:
            while self.running:
                try:
                    price_binance = self.binance.fetch_ticker(self.symbol)['last']
                    price_kucoin = self.kucoin.fetch_ticker(self.symbol)['last']

                    if price_binance > price_kucoin:
                        spread = price_binance - price_kucoin
                        spread_percent = (spread / price_kucoin) * 100
                        
                        if spread_percent > self.max_spread:
                            self.max_spread = spread_percent
                        
                        if spread_percent >= self.min_spread_percent and self.funds >= self.trade_amount:
                            btc_bought = self.trade_amount / price_kucoin
                            sell_value = btc_bought * price_binance
                            buy_fee = self.trade_amount * self.taker_fee
                            sell_fee = sell_value * self.taker_fee
                            net_profit = sell_value - self.trade_amount - buy_fee - sell_fee

                            if net_profit > 0:
                                self.funds += net_profit
                                self.cumulative_profit += net_profit
                                
                                with app.app_context():
                                    trade = Trade(
                                        buy_exchange='KuCoin',
                                        sell_exchange='Binance',
                                        buy_price=price_kucoin,
                                        sell_price=price_binance,
                                        amount=btc_bought,
                                        profit=net_profit
                                    )
                                    db.session.add(trade)
                                    db.session.commit()

                except Exception as e:
                    self.logger.error(f"Error: {str(e)}")
                    time.sleep(5)
                
                time.sleep(10)
        
        except KeyboardInterrupt:
            self.running = False

# --- Web Routes ---
bot = ArbitrageBot()

@app.route('/')
def dashboard():
    trades = Trade.query.order_by(Trade.timestamp.desc()).limit(10).all()
    return render_template('index.html', 
                         balance=bot.funds,
                         profit=bot.cumulative_profit,
                         trades=trades,
                         max_spread=bot.max_spread)

@app.route('/start', methods=['GET'])
def start_bot():
    if not bot.running:
        bot_thread = threading.Thread(target=bot.run)
        bot_thread.daemon = True
        bot_thread.start()
        return jsonify({'status': 'Bot started'})
    return jsonify({'status': 'Bot is already running'})

@app.route('/stop', methods=['GET'])
def stop_bot():
    bot.running = False
    return jsonify({'status': 'Bot stopped'})

@app.route('/status')
def get_status():
    return jsonify({
        'status': 'running' if bot.running else 'stopped',
        'balance': bot.funds,
        'profit': bot.cumulative_profit,
        'max_spread': bot.max_spread
    })

@app.route('/trades')
def get_trades():
    trades = Trade.query.order_by(Trade.timestamp.desc()).limit(50).all()
    return jsonify([{
        'buy_exchange': trade.buy_exchange,
        'sell_exchange': trade.sell_exchange,
        'buy_price': trade.buy_price,
        'sell_price': trade.sell_price,
        'amount': trade.amount,
        'profit': trade.profit,
        'timestamp': trade.timestamp.strftime('%Y-%m-%d %H:%M:%S')
    } for trade in trades])

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5001)