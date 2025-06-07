from flask import Flask, request
import os
import telebot
import requests
from PIL import Image, ImageEnhance, ImageFilter
from io import BytesIO
import pytesseract
from collections import defaultdict
from datetime import datetime
import threading
import time

app = Flask(__name__)

TOKEN = "7389304184:AAFN0HiOvWlCuUDwvGDFny3JC0EtQPJqHOA"
bot = telebot.TeleBot(TOKEN)

# Menü-Befehle setzen
bot.set_my_commands([
    telebot.types.BotCommand("alarme", "Alle aktiven Alarme anzeigen"),
    telebot.types.BotCommand("start", "Begrüßung & Beispiele anzeigen"),
    telebot.types.BotCommand("hilfe", "Alle Funktionen anzeigen"),
    telebot.types.BotCommand("status", "Letzte analysierte Position anzeigen"),
    telebot.types.BotCommand("position", "Neue Position analysieren")
])

COIN_PRICE_API = "https://fapi.binance.com/fapi/v1/ticker/price?symbol={symbol}"
user_thresholds = defaultdict(lambda: 20)
user_alert_enabled = defaultdict(lambda: True)
last_result = defaultdict(list)
position_entries = defaultdict(list)

def parse_position_text(text):
    lines = text.strip().split("
")
    results = []
    for line in lines:
        parts = line.strip().replace(",", ".").split()
        if len(parts) >= 4:
            try:
                symbol, entry, levx, direction = parts[:4]
                leverage = int(levx.lower().replace('x', ''))
                results.append((symbol.upper(), float(entry), leverage, direction.lower()))
            except:
                continue
    return results

def calculate_liq(entry, leverage, direction):
    if direction == 'long':
        return entry * (1 - 1 / leverage)
    elif direction == 'short':
        return entry * (1 + 1 / leverage)
    return 0

def get_current_price(symbol):
    try:
        response = requests.get(COIN_PRICE_API.format(symbol=symbol.replace("/", "")))
        data = response.json()
        return float(data['price'])
    except:
        return None

def distance_to_liq(current_price, liq_price, direction):
    if direction == 'long':
        return ((current_price - liq_price) / current_price) * 100
    else:
        return ((liq_price - current_price) / current_price) * 100

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "👋 Willkommen! Ich kann folgende Dinge für dich tun:

"
                          "📍 Einfach Position schreiben wie:
BTCUSDT 43200 10X Long

"
                          "📷 Screenshot senden → Ich erkenne deine Position automatisch

"
                          "💡 Befehle:
/hilfe – Übersicht aller Funktionen")

@bot.message_handler(commands=['alarm'])
def set_alarm_threshold(message):
    try:
        value = int(message.text.split()[1])
        user_thresholds[message.chat.id] = value
        bot.send_message(message.chat.id, f"🔔 Alarmgrenze auf {value}% gesetzt.")
    except:
        bot.send_message(message.chat.id, "⚠️ Bitte gib die Schwelle in % an, z. B.: /alarm 15")

@bot.message_handler(commands=['alertoff'])
def alertoff(message):
    user_alert_enabled[message.chat.id] = False
    bot.send_message(message.chat.id, "🔕 Alarmbenachrichtigungen deaktiviert.")

@bot.message_handler(commands=['alerton'])
def alerton(message):
    user_alert_enabled[message.chat.id] = True
    bot.send_message(message.chat.id, "🔔 Alarmbenachrichtigungen aktiviert.")

@bot.message_handler(commands=['alarme'])
def list_active_alarms(message):
    if message.chat.id not in last_result:
        bot.send_message(message.chat.id, "⚠️ Keine gespeicherten Positionen.")
        return
    alerts = [entry for entry in last_result[message.chat.id] if "⚠️ Gefahr" in entry]
    if alerts:
        response = '📣 Aktive Alarme unter deiner Schwelle:

' + '
'.join(alerts)
    else:
        response = '✅ Keine akuten Alarme unter deiner Schwelle.'
    bot.send_message(message.chat.id, response)

@bot.message_handler(commands=['hilfe'])
def hilfe(message):
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("📊 Position senden", callback_data="send_pos"))
    markup.add(telebot.types.InlineKeyboardButton("📷 Screenshot senden", callback_data="send_img"))
    markup.add(telebot.types.InlineKeyboardButton("⚠️ Alarmgrenze erklären", callback_data="explain_alarm"))
    bot.send_message(message.chat.id, "📌 Funktionen des Bots:

"
                                      "1️⃣ Textanalyse – z. B. 'ETHUSDT 3100 5X Long'
"
                                      "2️⃣ Screenshot-Erkennung deiner Position
"
                                      "3️⃣ Berechnung von Liquidationspreis
"
                                      "4️⃣ Live-Marktpreis & % Abstand
"
                                      "5️⃣ ⚠️ Alarm bei <20 % Abstand zum Liq-Level

"
                                      "6️⃣ /alarm [Prozent] – Eigene Alarmgrenze setzen

"
                                      "Wähle unten eine Aktion:", reply_markup=markup)

@bot.message_handler(commands=['status'])
def status(message):
    if message.chat.id in last_result and last_result[message.chat.id]:
        response = '📊 Aktuelle gespeicherte Positionen:

'
        for i, entry in enumerate(last_result[message.chat.id], 1):
            response += f"{i}. {entry}
"
        response += "
❌ Zum Löschen einer Position: /delete [Nummer]"
        bot.send_message(message.chat.id, response)
    else:
        bot.send_message(message.chat.id, "⚠️ Keine gespeicherten Positionen.")

@bot.message_handler(commands=['delete'])
def delete_position(message):
    try:
        index = int(message.text.split()[1]) - 1
        if message.chat.id in last_result and 0 <= index < len(last_result[message.chat.id]):
            deleted = last_result[message.chat.id].pop(index)
            bot.send_message(message.chat.id, f"🗑️ Gelöscht: {deleted}")
        else:
            bot.send_message(message.chat.id, "❌ Ungültige Nummer.")
    except:
        bot.send_message(message.chat.id, "⚠️ Bitte gib eine Nummer an: /delete 1")

@bot.message_handler(commands=['position'])
def position(message):
    bot.send_message(message.chat.id, "✏️ Bitte gib deine Position ein (z. B. BTCUSDT 30000 10X Long)")

@bot.message_handler(content_types=['text'])
def handle_text(message):
    positions = parse_position_text(message.text)
    reply = "📊 Liquidation & Risiko-Check:
"
    new_results = []
    for symbol, entry, lev, direction in positions:
        liq = calculate_liq(entry, lev, direction)
        price = get_current_price(symbol)
        if price:
            dist = distance_to_liq(price, liq, direction)
            threshold = user_thresholds[message.chat.id]
            warn = "⚠️ Gefahr!" if dist < threshold else "✅ Sicher"
            ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
            change = ""
            for e in position_entries[message.chat.id]:
                if e['symbol'] == symbol:
                    old_price = e['price']
                    change_pct = ((price - old_price) / old_price) * 100
                    change = f" (∆ {change_pct:+.2f}%)"
            entry_obj = {'symbol': symbol, 'entry': entry, 'price': price, 'ts': ts}
            position_entries[message.chat.id].append(entry_obj)
            line = f"{symbol}: Entry {entry} / Price {price:.5f} / Liq {liq:.5f} / Dist {dist:.2f}% → {warn} @ {ts}{change}
"
            reply += line
            chart_url = f"https://www.tradingview.com/x/?symbol=BINANCE:{symbol}"
            reply += f"📈 [Chart öffnen]({chart_url})
"
            new_results.append(line)
        else:
            reply += f"{symbol}: Preis nicht abrufbar.
"
    bot.reply_to(message, reply, parse_mode="Markdown")
    last_result[message.chat.id] = new_results

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    file_id = message.photo[-1].file_id
    file_info = bot.get_file(file_id)
    file = bot.download_file(file_info.file_path)
    image = Image.open(BytesIO(file))

    image = image.convert('L')
    image = image.filter(ImageFilter.MedianFilter())
    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(2)

    text = pytesseract.image_to_string(image)
    positions = parse_position_text(text)
    if not positions:
        bot.reply_to(message, "Konnte keine gültige Position aus dem Bild extrahieren.")
        return
    reply = "📷 Positionen aus Screenshot:
"
    for symbol, entry, lev, direction in positions:
        liq = calculate_liq(entry, lev, direction)
        price = get_current_price(symbol)
        if price:
            dist = distance_to_liq(price, liq, direction)
            warn = "⚠️ Gefahr!" if dist < user_thresholds[message.chat.id] else "✅ Sicher"
            reply += f"{symbol}: Entry {entry} / Price {price:.5f} / Liq {liq:.5f} / Dist {dist:.2f}% → {warn}
"
        else:
            reply += f"{symbol}: Preis nicht abrufbar.
"
    bot.reply_to(message, reply)

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    if call.data == "send_pos":
        bot.send_message(call.message.chat.id, "✏️ Sende deine Position z. B.:
BTCUSDT 30000 10X Long")
    elif call.data == "send_img":
        bot.send_message(call.message.chat.id, "📷 Sende jetzt deinen Screenshot mit der Position")
    elif call.data == "explain_alarm":
        bot.send_message(call.message.chat.id, "⚠️ Der Alarm wird ausgelöst, wenn der Abstand zum Liquidationspreis unter deiner definierten Schwelle fällt.")

@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    bot.process_new_updates([telebot.types.Update.de_json(request.stream.read().decode("utf-8"))])
    return '', 200

@app.route("/", methods=["GET"])
def index():
    return "Bot aktiv", 200

def background_alerts():
    while True:
        for chat_id, entries in last_result.items():
            if not user_alert_enabled[chat_id]:
                continue
            for reply in entries:
                if "⚠️ Gefahr" in reply:
                    bot.send_message(chat_id, "⏰ Warnung: Eine deiner Positionen ist unter deiner Liq-Grenze!")
                    break
        time.sleep(60)

if __name__ == '__main__':
    threading.Thread(target=background_alerts, daemon=True).start()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
