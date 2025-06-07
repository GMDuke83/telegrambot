from flask import Flask, request
import telebot
import os
import requests
from datetime import datetime
from PIL import Image
import pytesseract
from io import BytesIO

TOKEN = "7389304184:AAFN0HiOvWlCuUDwvGDFny3JC0EtQPJqHOA"
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# Kommandos
bot.set_my_commands([
    telebot.types.BotCommand("start", "Begrüßung anzeigen"),
    telebot.types.BotCommand("hilfe", "Funktionen anzeigen"),
    telebot.types.BotCommand("position", "Neue Position eingeben"),
    telebot.types.BotCommand("status", "Letzte gespeicherte Position anzeigen"),
    telebot.types.BotCommand("alarme", "Alle aktiven Alarme anzeigen")
])

positions = []
alarm_threshold = 20  # Standardwert in Prozent

COIN_PRICE_API = "https://fapi.binance.com/fapi/v1/ticker/price?symbol={symbol}"

def parse_position(text):
    try:
        parts = text.upper().split()
        symbol = parts[0].replace("/", "").replace("USDT", "") + "USDT"
        entry = float([p for p in parts if "." in p or p.isdigit()][0])
        lev = int([p.replace("X", "") for p in parts if "X" in p][0])
        side = "SHORT" if "SHORT" in parts else "LONG"
        return {"symbol": symbol, "entry": entry, "lev": lev, "side": side}
    except:
        return None

def get_price(symbol):
    url = COIN_PRICE_API.format(symbol=symbol)
    r = requests.get(url)
    if r.status_code == 200:
        return float(r.json()['price'])
    return None

def calculate_liq(entry, lev, side):
    if side == "LONG":
        return entry * (1 - 1 / lev)
    else:
        return entry * (1 + 1 / lev)

@bot.message_handler(commands=['start'])
def start(msg):
    bot.send_message(msg.chat.id, "👋 Hallo! Ich bin aktiv. Sende mir eine Position (z.B. `BTCUSDT 30000 x5 long`) oder ein Screenshot deiner Position.", parse_mode="Markdown")

@bot.message_handler(commands=['hilfe'])
def help(msg):
    bot.send_message(msg.chat.id, "Verfügbare Befehle:\n/start – Startmeldung\n/position – Neue Position\n/status – Zeige letzte Position\n/alarme – Liste aktiver Alarme\n/hilfe – Übersicht")

@bot.message_handler(commands=['position'])
def position(msg):
    bot.send_message(msg.chat.id, "Bitte sende deine Position z.B. `ETHUSDT 2500 x10 short`")

@bot.message_handler(commands=['status'])
def status(msg):
    if not positions:
        bot.send_message(msg.chat.id, "❗ Keine Position gespeichert.")
    else:
        last = positions[-1]
        now = datetime.utcnow().strftime('%H:%M:%S')
        bot.send_message(msg.chat.id, f"📊 {last['symbol']}, {last['entry']} {last['side']} {last['lev']}x\n📌 Letzte Analyse: {now}")

@bot.message_handler(commands=['alarme'])
def alarme(msg):
    if not positions:
        bot.send_message(msg.chat.id, "📭 Keine aktiven Alarme.")
        return
    out = "\n".join([f"{p['symbol']} {p['side']} {p['lev']}x" for p in positions])
    bot.send_message(msg.chat.id, "🔔 Aktive Alarme:\n" + out)

@bot.message_handler(content_types=['text'])
def handle_text(msg):
    pos = parse_position(msg.text)
    if not pos:
        bot.send_message(msg.chat.id, "⚠️ Konnte die Position nicht erkennen.")
        return

    price = get_price(pos['symbol'])
    if not price:
        bot.send_message(msg.chat.id, f"🔍 Preis für {pos['symbol']} nicht gefunden.")
        return

    liq = calculate_liq(pos['entry'], pos['lev'], pos['side'])
    abstand = abs((price - liq) / price * 100)
    warn = "✅ Sicher" if abstand > alarm_threshold else "⚠️ *Gefahr!*"
    txt = f"📈 *Liquidation Check*\n{pos['symbol']}: Entry {pos['entry']} / Leverage {pos['lev']}x / {pos['side']}\n→ Aktueller Preis: {price:.4f}\n→ Liquidation: {liq:.4f}\n→ Abstand: {abstand:.2f}%\n{warn}"
    bot.send_message(msg.chat.id, txt, parse_mode="Markdown")
    pos['timestamp'] = datetime.utcnow().isoformat()
    positions.append(pos)

@bot.message_handler(content_types=['photo'])
def handle_photo(msg):
    file_info = bot.get_file(msg.photo[-1].file_id)
    file = bot.download_file(file_info.file_path)
    image = Image.open(BytesIO(file)).convert('L')
    text = pytesseract.image_to_string(image)
    msg.text = text
    handle_text(msg)

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    json_string = request.stream.read().decode("utf-8")
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return '', 200

@app.route("/")
def index():
    return "Bot aktiv", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
