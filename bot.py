import telebot
import sqlite3
import time
import os
from dotenv import load_dotenv
from profile_module import register_profile_handlers
from random_module import register_random_handlers
from currency_module import register_currency_handlers
from activity_module import register_activity_handlers
from inventory_module import register_inventory_handlers
from market_module import register_market_handlers
from battle_module import register_battle_handlers

load_dotenv()
TOKEN = os.getenv('TOKEN')
bot = telebot.TeleBot(TOKEN)

def setup_database():
    conn = sqlite3.connect('percy_jackson_bot.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            demigod_parent TEXT,
            pronouns TEXT,
            drachmas INTEGER DEFAULT 0,
            energy INTEGER DEFAULT 15,
            last_drachma_time INTEGER DEFAULT 0,
            strength REAL DEFAULT 8,
            health INTEGER DEFAULT 100,
            defense INTEGER DEFAULT 7,
            equipped_item TEXT,
            last_energy_restore_time INTEGER DEFAULT 0
        )
    ''')
    
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN drachmas INTEGER DEFAULT 0")
        cursor.execute("ALTER TABLE users ADD COLUMN energy INTEGER DEFAULT 15")
        cursor.execute("ALTER TABLE users ADD COLUMN last_drachma_time INTEGER DEFAULT 0")
        cursor.execute("ALTER TABLE users ADD COLUMN strength REAL DEFAULT 8")
        cursor.execute("ALTER TABLE users ADD COLUMN health INTEGER DEFAULT 100")
        cursor.execute("ALTER TABLE users ADD COLUMN defense INTEGER DEFAULT 7")
        cursor.execute("ALTER TABLE users ADD COLUMN equipped_item TEXT")
        cursor.execute("ALTER TABLE users ADD COLUMN last_energy_restore_time INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS inventory (
            user_id INTEGER,
            item_id TEXT,
            quantity INTEGER,
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS quotes (
            quote_id INTEGER PRIMARY KEY,
            quote_text TEXT,
            author_id INTEGER,
            author_name TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stickers (
            sticker_id TEXT PRIMARY KEY
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS market (
            item_id TEXT PRIMARY KEY,
            special_offer_price REAL,
            special_offer_end_time INTEGER
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS market_items_for_sale (
            item_id TEXT,
            item_name TEXT,
            item_price INTEGER,
            last_updated INTEGER
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS active_raids (
            raid_id INTEGER PRIMARY KEY AUTOINCREMENT,
            monster_id TEXT,
            status TEXT,
            start_time INTEGER,
            end_time INTEGER,
            raid_channel INTEGER,
            raid_message_id INTEGER
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS raid_participants (
            raid_id INTEGER,
            user_id INTEGER,
            username TEXT,
            damage_received REAL DEFAULT 0,
            FOREIGN KEY(raid_id) REFERENCES active_raids(raid_id),
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        )
    ''')
    
    conn.commit()
    conn.close()

def restore_energy(user_id):
    conn = sqlite3.connect('percy_jackson_bot.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT energy, last_energy_restore_time FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    
    if result:
        current_energy, last_time = result
        current_time = int(time.time())
        max_energy = 15
        
        if last_time == 0:
            last_time = current_time

        elapsed_time = current_time - last_time
        restored_units = elapsed_time // 1800
        
        if restored_units > 0 and current_energy < max_energy:
            new_energy = min(current_energy + restored_units, max_energy)
            new_last_time = last_time + restored_units * 1800
            cursor.execute('UPDATE users SET energy = ?, last_energy_restore_time = ? WHERE user_id = ?',
                           (new_energy, new_last_time, user_id))
            conn.commit()
    
    conn.close()

def energy_restore_middleware(message):
    user_id = message.from_user.id
    restore_energy(user_id)
    
if __name__ == "__main__":
    setup_database()
    
    register_profile_handlers(bot)
    register_random_handlers(bot)
    register_currency_handlers(bot)
    register_activity_handlers(bot)
    register_inventory_handlers(bot)
    register_market_handlers(bot)
    register_battle_handlers(bot)

    bot.message_handler(func=lambda m: True)(lambda m: energy_restore_middleware(m))
    bot.callback_query_handler(func=lambda c: True)(lambda c: energy_restore_middleware(c.message))

    print("Бот запущено...")
    bot.polling(none_stop=True)