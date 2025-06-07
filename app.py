from flask import Flask, request
import telebot
import os

TOKEN = "7389304184:AAFN0HiOvWlCuUDwvGDFny3JC0EtQPJqHOA"
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# Beispiel-Befehl
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "👋 Hallo! Ich bin aktiv und bereit.")

# Webhook-Handler für Telegram POST-Anfragen
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    json_string = request.stream.read().decode("utf-8")
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return '', 200

# Health-Check
@app.route("/", methods=["GET"])
def index():
    return "Bot läuft!", 200

# Lokaler oder Render-Start
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
