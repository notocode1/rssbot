import telebot
import feedparser
import time
import threading
import os

TOKEN = os.environ.get("TOKEN")
RSS_FEED_URL = os.environ.get("RSS_URL")

bot = telebot.TeleBot(TOKEN)
subscribers = set()
sent_links = set()

@bot.message_handler(commands=['start'])
def start(message):
    chat_id = message.chat.id
    subscribers.add(chat_id)
    bot.send_message(chat_id, "✅ Subscribed! You’ll get updates automatically.")

def check_feed():
    while True:
        feed = feedparser.parse(RSS_FEED_URL)
        for entry in feed.entries[:5]:
            if entry.link not in sent_links:
                msg = f"📰 {entry.title}\n{entry.link}"
                for user in subscribers:
                    try:
                        bot.send_message(user, msg)
                    except:
                        pass
                sent_links.add(entry.link)
        time.sleep(300)

threading.Thread(target=check_feed).start()
bot.polling()
