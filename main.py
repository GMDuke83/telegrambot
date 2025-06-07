import requests
import time
import telegram

# === CONFIG ===
bot_token = '7389304184:AAFN0HiOvWICuUDvwGDFny3JCOEtQPJqH0A'
chat_id = 1617275771
coins = {
    'HBARUSDT': {'ref': 0.16932, 'liq': 0.11162},
    'SOLUSDT': {'ref': 150.613, 'liq': 99.437},
    'XRPUSDT': {'ref': 2.1789, 'liq': 1.5537}
}
threshold = 30  # Prozent Abstand zum Liquidationspreis
interval = 60  # Sekundentakt

# === INIT TELEGRAM ===
bot = telegram.Bot(token=bot_token)

# === FUNKTION ===
def check_liq_alert():
    for symbol, data in coins.items():
        url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
        response = requests.get(url)
        current_price = float(response.json()['price'])

        liq = data['liq']
        distance = ((current_price - liq) / current_price) * 100

        if distance < threshold:
            message = (f"⚠️ {symbol} nähert sich dem Liquidationspreis!\n"
                       f"Aktueller Preis: {current_price:.5f} USDT\n"
                       f"Liq.-Preis: {liq:.5f} USDT\n"
                       f"Abstand: {distance:.2f}%")
            bot.send_message(chat_id=chat_id, text=message)

# === LOOP ===
while True:
    try:
        check_liq_alert()
    except Exception as e:
        print(f"Fehler: {e}")
    time.sleep(interval)