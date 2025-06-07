from flask import Flask, request
import os
import telebot
import requests
from PIL import Image
from io import BytesIO
import pytesseract

app = Flask(__name__)

TOKEN = "7389304184:AAFN0HiOvWlCuUDwvGDFny3JC0EtQPJqHOA"
bot = telebot.TeleBot(TOKEN)

def parse_position_text(text):
    lines = text.strip().split("\n")
    results = []
    for line in lines:
        parts = line.strip().split()
        if len(parts) >= 4:
            symbol, entry, levx, direction = parts[:4]
            leverage = int(levx.lower().replace('x', ''))
            results.append((symbol.upper(), float(entry), leverage, direction.lower()))
    return results

def calculate_liq(entry, leverage, direction):
    if direction == 'long':
        return entry * (1 - 1 / leverage)
    elif direction == 'short':
        return entry * (1 + 1 / leverage)
    return 0

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "Sende mir einfach deine Positionen als Text oder Screenshot. Ich berechne deinen Liquidationspreis.")

@bot.message_handler(content_types=['text'])
def handle_text(message):
    positions = parse_position_text(message.text)
    reply = "\U0001F4CA Liquidation Check:\n"
    for symbol, entry, lev, direction in positions:
        liq = calculate_liq(entry, lev, direction)
        reply += f"{symbol}: Entry {entry} / Leverage {lev}x / {direction.upper()} → Liq: {liq:.5f}\n"
    bot.reply_to(message, reply)

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    file_id = message.photo[-1].file_id
    file_info = bot.get_file(file_id)
    file = bot.download_file(file_info.file_path)
    image = Image.open(BytesIO(file))
    text = pytesseract.image_to_string(image)
    positions = parse_position_text(text)
    if not positions:
        bot.reply_to(message, "Konnte keine gültige Position aus dem Bild extrahieren.")
        return
    reply = "📸 Erkannte Position(en):\n"
    for symbol, entry, lev, direction in positions:
        liq = calculate_liq(entry, lev, direction)
        reply += f"{symbol}: Entry {entry} / Leverage {lev}x / {direction.upper()} → Liq: {liq:.5f}\n"
    bot.reply_to(message, reply)

@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    bot.process_new_updates([telebot.types.Update.de_json(request.stream.read().decode("utf-8"))])
    return '', 200

@app.route("/", methods=["GET"])
def index():
    return "Bot aktiv", 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
