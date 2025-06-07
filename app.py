from flask import Flask, request
import os
import telebot
import requests
from PIL import Image, ImageEnhance, ImageFilter
from io import BytesIO
import pytesseract

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
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
