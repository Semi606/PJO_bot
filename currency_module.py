import telebot
import sqlite3
import random
import time
from db_utils import get_user_drachmas, add_drachmas_to_user

# Обробник команди /wallet
def show_wallet(message, bot):
    user_id = message.from_user.id
    
    drachmas = get_user_drachmas(user_id)
    
    if drachmas is None:
        bot.send_message(message.chat.id, "Схоже, у вас ще немає профілю. Використайте /create, щоб його створити.")
    else:
        bot.send_message(message.chat.id, f"💰 Ваш гаманець: {drachmas} драхм.")

# Обробник команди /getDrachma
def get_drachma(message, bot):
    user_id = message.from_user.id
    cooldown = 18000 # 5 годин у секундах
    
    conn = sqlite3.connect('percy_jackson_bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT last_drachma_time FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    
    if result is None:
        bot.send_message(message.chat.id, "Схоже, у вас ще немає профілю. Використайте /create, щоб його створити.")
        conn.close()
        return

    last_time = result[0]
    current_time = time.time()
    
    if current_time - last_time < cooldown:
        remaining_time = cooldown - (current_time - last_time)
        hours = int(remaining_time // 3600)
        minutes = int((remaining_time % 3600) // 60)
        bot.send_message(message.chat.id, f"⌛ Ви вже шукали драхми нещодавно. Спробуйте знову через {hours} год {minutes} хв.")
        conn.close()
        return
    
    amount = random.randint(1, 5)
    add_drachmas_to_user(user_id, amount)
    
    cursor.execute('UPDATE users SET last_drachma_time = ? WHERE user_id = ?', (current_time, user_id))
    conn.commit()
    conn.close()
    
    bot.send_message(message.chat.id, f"🎉 Ви знайшли {amount} драхм! Ваш баланс оновлено.")

# Функція для реєстрації обробників
def register_currency_handlers(bot):
    bot.message_handler(commands=['wallet'])(lambda m: show_wallet(m, bot))
    bot.message_handler(commands=['getDrachma'])(lambda m: get_drachma(m, bot))