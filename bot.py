import time
import telebot
from config import BOT_TOKEN
from db import init_db, save_group, get_last_seen_time
from commands import register_commands
from feeds import start_feed_loop

bot = telebot.TeleBot(BOT_TOKEN, parse_mode='MarkdownV2')

@bot.message_handler(func=lambda msg: msg.chat.type in ['group', 'supergroup'])
def on_group_message(msg):
    save_group(msg.chat.id, msg.chat.title, msg.chat.type)

def run_bot(config):
    init_db()
    start_time = get_last_seen_time() or time.time()
    register_commands(bot)
    start_feed_loop(bot, start_time)
    print("🚀 Bot is running")
    bot.infinity_polling()

# Ensure that the bot runs when this file is executed directly
if __name__ == "__main__":
    run_bot(config)
