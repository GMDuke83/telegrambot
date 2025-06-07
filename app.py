from flask import Flask, request
import requests
import telebot
import os

app = Flask(__name__)

# Dein Bot-Token
TOKEN = '7389304184:AAFN0HiOvWlCuUDwvGDFny3JC0EtQPJqHOA'
bot = telebot.TeleBot(TOKEN)

# Coins & Liquidationspreise
coins = {
    'HBARUSDT': {'liq': 0.11162},
    'SOLUSDT': {'liq': 99.437},
    'XRPUSDT': {'liq': 1.5537}
}

# Preisabfrage + Statusbericht generieren
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

# Render-Root Testseite
@app.route('/', methods=['GET'])
def home():
    return "Bot läuft.", 200

# Telegram Webhook-Eingang
@app.route(f'/{TOKEN}', methods=['POST'])
def telegram_webhook():
    update = request.get_json()
    if "message" in update and "text" in update["message"] and update["message"]["text"] == "/status":
        chat_id = update["message"]["chat"]["id"]
        bot.send_message(chat_id, fetch_status())
    return "", 200

# Wichtig für Render: bindet an 0.0.0.0 und Port aus Umgebung
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
