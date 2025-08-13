import sqlite3
import time
import random

# --- Функції для користувачів ---
def save_user_profile(user_id, username, parent=None, pronouns=None):
    conn = sqlite3.connect('percy_jackson_bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    existing_user = cursor.fetchone()

    if existing_user:
        cursor.execute('''
            UPDATE users SET username = ?, demigod_parent = ?, pronouns = ?
            WHERE user_id = ?
        ''', (username, parent or existing_user[2], pronouns or existing_user[3], user_id))
    else:
        cursor.execute('''
            INSERT INTO users (user_id, username, demigod_parent, pronouns, drachmas, energy, last_drachma_time, strength, health, defense, equipped_item, last_energy_restore_time)
            VALUES (?, ?, ?, ?, 0, 15, 0, 8, 100, 7, NULL, ?)
        ''', (user_id, username, parent, pronouns, int(time.time())))
    
    conn.commit()
    conn.close()

def get_user_profile(user_id):
    conn = sqlite3.connect('percy_jackson_bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    profile = cursor.fetchone()
    conn.close()
    if profile:
        return profile
    return None

def get_all_users():
    conn = sqlite3.connect('percy_jackson_bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT user_id, username FROM users')
    users = cursor.fetchall()
    conn.close()
    return users

# --- Функції для драхм та енергії ---
def get_user_drachmas(user_id):
    conn = sqlite3.connect('percy_jackson_bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT drachmas FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def add_drachmas_to_user(user_id, amount):
    conn = sqlite3.connect('percy_jackson_bot.db')
    cursor = conn.cursor()
    
    current_drachmas = get_user_drachmas(user_id)
    if current_drachmas is None:
        cursor.execute("INSERT OR IGNORE INTO users (user_id, drachmas) VALUES (?, ?)", (user_id, amount))
    else:
        new_drachmas = current_drachmas + amount
        cursor.execute('UPDATE users SET drachmas = ? WHERE user_id = ?', (new_drachmas, user_id))
    
    conn.commit()
    conn.close()

def get_user_energy(user_id):
    conn = sqlite3.connect('percy_jackson_bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT energy FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def set_user_energy(user_id, new_energy):
    conn = sqlite3.connect('percy_jackson_bot.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET energy = ? WHERE user_id = ?', (new_energy, user_id))
    conn.commit()
    conn.close()

def get_user_strength(user_id):
    conn = sqlite3.connect('percy_jackson_bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT strength FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def get_user_equipped_item(user_id):
    conn = sqlite3.connect('percy_jackson_bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT equipped_item FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def equip_item(user_id, item_id):
    conn = sqlite3.connect('percy_jackson_bot.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET equipped_item = ? WHERE user_id = ?', (item_id.strip(), user_id))
    conn.commit()
    conn.close()

def unequip_item(user_id):
    conn = sqlite3.connect('percy_jackson_bot.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET equipped_item = NULL WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

def increment_user_strength(user_id):
    conn = sqlite3.connect('percy_jackson_bot.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT strength FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    
    if result:
        strength = result[0]
        new_strength = strength + 0.5
        cursor.execute('UPDATE users SET strength = ? WHERE user_id = ?', (new_strength, user_id))
        
    conn.commit()
    conn.close()

# --- Функції для інвентарю ---
def get_user_inventory(user_id):
    conn = sqlite3.connect('percy_jackson_bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT item_id, quantity FROM inventory WHERE user_id = ?', (user_id,))
    items = cursor.fetchall()
    conn.close()
    return items

def get_item_quantity_in_inventory(user_id, item_id):
    conn = sqlite3.connect('percy_jackson_bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT quantity FROM inventory WHERE user_id = ? AND item_id = ?', (user_id, item_id.strip()))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 0

def get_random_inventory_item(user_id):
    conn = sqlite3.connect('percy_jackson_bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT item_id FROM inventory WHERE user_id = ? ORDER BY RANDOM() LIMIT 1', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def add_item_to_inventory(user_id, item_id, quantity=1):
    conn = sqlite3.connect('percy_jackson_bot.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT quantity FROM inventory WHERE user_id = ? AND item_id = ?', (user_id, item_id.strip()))
    result = cursor.fetchone()
    
    if result:
        new_quantity = result[0] + quantity
        cursor.execute('UPDATE inventory SET quantity = ? WHERE user_id = ? AND item_id = ?', (new_quantity, user_id, item_id.strip()))
    else:
        cursor.execute('INSERT INTO inventory (user_id, item_id, quantity) VALUES (?, ?, ?)', (user_id, item_id.strip(), quantity))
    
    conn.commit()
    conn.close()

def remove_item_from_inventory(user_id, item_id, quantity=1):
    conn = sqlite3.connect('percy_jackson_bot.db')
    cursor = conn.cursor()
    
    current_quantity = get_item_quantity_in_inventory(user_id, item_id.strip())
    
    if current_quantity > quantity:
        new_quantity = current_quantity - quantity
        cursor.execute('UPDATE inventory SET quantity = ? WHERE user_id = ? AND item_id = ?', (new_quantity, user_id, item_id.strip()))
    elif current_quantity <= quantity:
        cursor.execute('DELETE FROM inventory WHERE user_id = ? AND item_id = ?', (user_id, item_id.strip()))
    
    conn.commit()
    conn.close()

def clear_inventory(user_id):
    conn = sqlite3.connect('percy_jackson_bot.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM inventory WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

# --- Функції для цитат ---
def add_quote(quote_text, author_id, author_name):
    conn = sqlite3.connect('percy_jackson_bot.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO quotes (quote_text, author_id, author_name) VALUES (?, ?, ?)', (quote_text, author_id, author_name))
    conn.commit()
    conn.close()

def get_random_quote():
    conn = sqlite3.connect('percy_jackson_bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT quote_text, author_name FROM quotes ORDER BY RANDOM() LIMIT 1')
    result = cursor.fetchone()
    conn.close()
    return result

def add_sticker_to_db(sticker_id):
    conn = sqlite3.connect('percy_jackson_bot.db')
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO stickers (sticker_id) VALUES (?)', (sticker_id,))
    conn.commit()
    conn.close()

def get_random_sticker_from_db():
    conn = sqlite3.connect('percy_jackson_bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT sticker_id FROM stickers ORDER BY RANDOM() LIMIT 1')
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

# --- Функції для рейдів ---
def get_active_raid_info(chat_id):
    conn = sqlite3.connect('percy_jackson_bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM active_raids WHERE raid_channel = ? AND status IN (?, ?)', (chat_id, 'pending', 'in_progress'))
    result = cursor.fetchone()
    conn.close()
    return result

def create_raid_db(monster_id, chat_id, message_id):
    conn = sqlite3.connect('percy_jackson_bot.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO active_raids (monster_id, status, start_time, raid_channel, raid_message_id) VALUES (?, ?, ?, ?, ?)',
                   (monster_id, 'pending', int(time.time()), chat_id, message_id))
    conn.commit()
    raid_id = cursor.lastrowid
    conn.close()
    return raid_id

def add_raid_participant_db(raid_id, user_id, username):
    conn = sqlite3.connect('percy_jackson_bot.db')
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO raid_participants (raid_id, user_id, username) VALUES (?, ?, ?)',
                   (raid_id, user_id, username))
    conn.commit()
    conn.close()

def get_raid_participants_db(raid_id):
    conn = sqlite3.connect('percy_jackson_bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT user_id, username FROM raid_participants WHERE raid_id = ?', (raid_id,))
    result = cursor.fetchall()
    conn.close()
    return result

def update_raid_status_db(raid_id, status):
    conn = sqlite3.connect('percy_jackson_bot.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE active_raids SET status = ? WHERE raid_id = ?', (status, raid_id))
    conn.commit()
    conn.close()
    
def update_raid_participant_damage_db(raid_id, user_id, damage):
    conn = sqlite3.connect('percy_jackson_bot.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE raid_participants SET damage_received = damage_received + ? WHERE raid_id = ? AND user_id = ?',
                   (damage, raid_id, user_id))
    conn.commit()
    conn.close()

def get_raid_participants_with_damage_db(raid_id):
    conn = sqlite3.connect('percy_jackson_bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT user_id, username, damage_received FROM raid_participants WHERE raid_id = ?', (raid_id,))
    result = cursor.fetchall()
    conn.close()
    return result

def end_raid_db(raid_id):
    conn = sqlite3.connect('percy_jackson_bot.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM active_raids WHERE raid_id = ?', (raid_id,))
    cursor.execute('DELETE FROM raid_participants WHERE raid_id = ?', (raid_id,))
    conn.commit()
    conn.close()