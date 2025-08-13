import random
import os
import sqlite3
from db_utils import get_all_users

# Функція для завантаження компліментів з файлу
def load_compliments(filename='compliments.txt'):
    if not os.path.exists(filename):
        print(f"Помилка: Файл '{filename}' не знайдено.")
        return []
    with open(filename, 'r', encoding='utf-8') as f:
        compliments = [line.strip() for line in f if line.strip()]
    return compliments

# Обробник команди /random
def random_user_compliment(message, bot):
    if message.chat.type not in ['group', 'supergroup']:
        bot.send_message(message.chat.id, "Ця команда працює тільки в групових чатах.")
        return
    
    users = get_all_users()
    
    if not users:
        bot.send_message(message.chat.id, "У базі даних немає користувачів, не можу вибрати випадкового.")
        return
        
    compliments = load_compliments()
    if not compliments:
        bot.send_message(message.chat.id, "Список компліментів порожній.")
        return

    random_user_id, random_username = random.choice(users)
    random_compliment = random.choice(compliments)
    
    mention = f"[{random_username}](tg://user?id={random_user_id})"
    
    compliment_message = f"{mention}, {random_compliment}"
    
    bot.send_message(message.chat.id, compliment_message, parse_mode='Markdown')

# Функція для реєстрації обробників
def register_random_handlers(bot):
    bot.message_handler(commands=['random'])(lambda m: random_user_compliment(m, bot))