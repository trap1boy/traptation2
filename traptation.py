# ✅ keep_alive.py
from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "I'm alive"

def keep_alive():
    Thread(target=lambda: app.run(host='0.0.0.0', port=8080)).start()


# ✅ bot.py
import telebot
from telebot import types
from deep_translator import GoogleTranslator
import requests
import openai
import pytesseract
from PIL import Image
import io
import speech_recognition as sr
from pydub import AudioSegment
import os
from keep_alive import keep_alive

BOT_TOKEN = '7718204885:AAFJX06SzcwwaW2Ep1rWHp8akL32A1TiTSw'

ADMIN_ID = 7829262788
CHANNEL_USERNAME = '@ixtrap'
OPENAI_API_KEY = 'YOUR_OPENAI_API_KEY'
openai.api_key = OPENAI_API_KEY
bot = telebot.TeleBot(BOT_TOKEN)

user_set = set()

# ------------------------------ CHANNEL CHECK -----------------------------
def is_user_subscribed(user_id):
    try:
        status = bot.get_chat_member(CHANNEL_USERNAME, user_id).status
        return status in ['member', 'creator', 'administrator']
    except:
        return False

def send_subscription_prompt(chat_id):
    markup = types.InlineKeyboardMarkup()
    btn = types.InlineKeyboardButton("✅ Join Channel", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")
    markup.add(btn)
    bot.send_message(chat_id, f"✌️ Subscribe to our channel to continue:\n⛔️ Please join {CHANNEL_USERNAME} first.", reply_markup=markup)

# ------------------------------ START -----------------------------
@bot.message_handler(commands=['start'])
def start(message):
    if not is_user_subscribed(message.chat.id):
        send_subscription_prompt(message.chat.id)
        return

    user_set.add(message.chat.id)
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("📚 Dictionary", "🔤 Translate")
    markup.row("🧠 ChatGPT", "💬 Feedback")
    markup.row("📸 Image Translate", "🎤 Voice Translate")
    bot.send_message(message.chat.id, "Hey there!\n\nChoose an option:", reply_markup=markup)

# ------------------------------ FEEDBACK -----------------------------
@bot.message_handler(func=lambda msg: msg.text == "💬 Feedback")
def feedback_handler(message):
    bot.send_message(message.chat.id, "✍️ Send your feedback:")
    bot.register_next_step_handler(message, forward_feedback)

def forward_feedback(message):
    bot.send_message(ADMIN_ID, f"📬 Feedback from {message.chat.id}:\n{message.text}")
    bot.send_message(message.chat.id, "✅ Thanks for your feedback!")

# ------------------------------ CHATGPT -----------------------------
@bot.message_handler(func=lambda msg: msg.text == "🧠 ChatGPT")
def chatgpt_handler(message):
    bot.send_message(message.chat.id, "🧠 Ask me anything:")
    bot.register_next_step_handler(message, ask_chatgpt)

def ask_chatgpt(message):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": message.text}]
        )
        bot.send_message(message.chat.id, response.choices[0].message.content)
    except:
        bot.send_message(message.chat.id, "❌ GPT Error")

# ------------------------------ TRANSLATE TEXT -----------------------------
@bot.message_handler(func=lambda msg: msg.text == "🔤 Translate")
def translate_handler(message):
    if not is_user_subscribed(message.chat.id):
        send_subscription_prompt(message.chat.id)
        return
    bot.send_message(message.chat.id, "🌐 Send the text you want to translate (EN <-> FA):")
    bot.register_next_step_handler(message, do_translate)

def do_translate(message):
    try:
        translated = GoogleTranslator(source='auto', target='fa' if message.text.isascii() else 'en').translate(message.text)
        bot.send_message(message.chat.id, f"🌍 Translation:\n{translated}")
    except:
        bot.send_message(message.chat.id, "❌ Could not translate.")

# ------------------------------ DICTIONARY -----------------------------
@bot.message_handler(func=lambda msg: msg.text == "📚 Dictionary")
def dictionary_mode(message):
    if not is_user_subscribed(message.chat.id):
        send_subscription_prompt(message.chat.id)
        return
    bot.send_message(message.chat.id, "Send me any word you want to get meanings for ✌️")
    bot.register_next_step_handler(message, handle_word)

def handle_word(message):
    if not is_user_subscribed(message.chat.id):
        send_subscription_prompt(message.chat.id)
        return
    word = message.text.lower()
    try:
        res = requests.get(f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}").json()[0]
        phonetics = res.get("phonetics", [])
        meanings = res.get("meanings", [])
        synonyms = set()
        antonyms = set()
        text_phonetic = ""
        uk_audio = us_audio = ""

        for p in phonetics:
            if not text_phonetic and p.get("text"):
                text_phonetic = p["text"]
            if p.get("audio"):
                if "uk.mp3" in p["audio"]:
                    uk_audio = p["audio"]
                elif "us.mp3" in p["audio"]:
                    us_audio = p["audio"]

        defs = []
        examples = []
        for m in meanings:
            for d in m.get("definitions", []):
                if d.get("definition"):
                    defs.append(f"❓ {d['definition']}")
                if d.get("example"):
                    examples.append(d["example"])
                synonyms.update(d.get("synonyms", []))
                antonyms.update(d.get("antonyms", []))

        if not defs:
            prompt = f"Give definition, 2 examples, synonyms and antonyms for the English word: '{word}'"
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}]
            )
            bot.send_message(message.chat.id, response.choices[0].message.content)
            return

        reply = f"📚 {word.capitalize()}\n\n"
        reply += f"🔉 {text_phonetic}\n\n"
        reply += defs[0] + "\n\n" if defs else ""

        if examples:
            reply += "❗️ Examples:\n\n"
            for idx, ex in enumerate(examples[:3], start=1):
                reply += f"{idx}. {ex}\n"

        if synonyms:
            reply += f"\n🟩 Synonyms: {', '.join(list(synonyms)[:5])}"
        if antonyms:
            reply += f"\n🟥 Antonyms: {', '.join(list(antonyms)[:5])}"

        reply += "\n━━━━━━━━━━━━━\n🌀 @ixtrap"
        bot.send_message(message.chat.id, reply)

        if uk_audio:
            bot.send_audio(message.chat.id, uk_audio)
        elif us_audio:
            bot.send_audio(message.chat.id, us_audio)

    except:
        bot.send_message(message.chat.id, "❌ Word not found or error occurred.")

# ------------------------------ TRANSLATE IMAGE -----------------------------
@bot.message_handler(content_types=['photo'])
def handle_image(message):
    if not is_user_subscribed(message.chat.id):
        send_subscription_prompt(message.chat.id)
        return

    file_info = bot.get_file(message.photo[-1].file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    image = Image.open(io.BytesIO(downloaded_file))
    text = pytesseract.image_to_string(image)

    if not text.strip():
        bot.send_message(message.chat.id, "❌ No text detected in image.")
        return

    translated = GoogleTranslator(source='auto', target='fa' if text.isascii() else 'en').translate(text)
    bot.send_message(message.chat.id, f"📸 Translated Text:\n{translated}")

# ------------------------------ TRANSLATE VOICE -----------------------------
@bot.message_handler(content_types=['voice'])
def handle_voice(message):
    if not is_user_subscribed(message.chat.id):
        send_subscription_prompt(message.chat.id)
        return

    file_info = bot.get_file(message.voice.file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    ogg_path = "voice.ogg"
    wav_path = "voice.wav"
    with open(ogg_path, 'wb') as f:
        f.write(downloaded_file)

    AudioSegment.from_ogg(ogg_path).export(wav_path, format="wav")

    recognizer = sr.Recognizer()
    with sr.AudioFile(wav_path) as source:
        audio_data = recognizer.record(source)
        try:
            text = recognizer.recognize_google(audio_data)
            translated = GoogleTranslator(source='auto', target='fa' if text.isascii() else 'en').translate(text)
            bot.send_message(message.chat.id, f"🎤 Translated Voice:\n{text}\n➡️ {translated}")
        except:
            bot.send_message(message.chat.id, "❌ Could not recognize voice.")

    os.remove(ogg_path)
    os.remove(wav_path)

# ------------------------------ ADMIN STATS -----------------------------
@bot.message_handler(commands=['users'])
def user_stats(message):
    if message.chat.id == ADMIN_ID:
        bot.send_message(message.chat.id, f"📊 Total Users: {len(user_set)}")

# ✅ فعال نگه داشتن سرور
keep_alive()
bot.infinity_polling()
