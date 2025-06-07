from flask import Flask, request
import requests
import telebot

app = Flask(__name__)

TOKEN = '7389304184:AAFN0HiOvWlCuUDvwGDFny3JC0EtQPJqHOA'
bot = telebot.TeleBot(TOKEN)
URL = f"https://api.telegram.org/bot{TOKEN}/"

coins = {
    'HBARUSDT': {'liq': 0.11162},
    'SOLUSDT': {'liq': 99.437},
    'XRPUSDT': {'liq': 1.5537}
}

def fetch_status():
    message = '📊 Liquidation Status:\n'
    for symbol, data in coins.items():
        try:
            res = requests.get(f'https://api.binance.com/api/v3/ticker/price?symbol={symbol}')
            price = float(res.json()['price'])
            liq = data['liq']
            diff = ((price - liq) / price) * 100
            status = '✅ Sicher' if diff > 30 else '⚠️ Gefahr!'
            message += f"\n{symbol}: {price:.4f} USDT\nAbstand: {diff:.2f}% – {status}\n"
        except:
            message += f"\n{symbol}: Fehler beim Abrufen\n"
    return message

@app.route('/', methods=['GET'])
def home():
    return "Bot läuft.", 200

@app.route(f'/{TOKEN}', methods=['POST'])
def telegram_webhook():
    update = request.get_json()
    if "message" in update and "text" in update["message"] and update["message"]["text"] == "/status":
        chat_id = update["message"]["chat"]["id"]
        bot.send_message(chat_id, fetch_status())
    return "", 200

if __name__ == '__main__':
    app.run()