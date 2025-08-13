import telebot
import sqlite3
import random
import time
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# Припустимо, що ці модулі та їх функції вже існують
from loot_items import LOOT_ITEMS, get_item_info, get_random_loot
from db_utils import add_drachmas_to_user, get_user_drachmas, get_user_inventory, remove_item_from_inventory, add_item_to_inventory, get_item_quantity_in_inventory, get_user_equipped_item, clear_inventory

# Налаштування ринку
SPECIAL_OFFER_COOLDOWN = 20 * 3600 # 20 годин
SPECIAL_OFFER_DURATION = 2 * 3600 # 2 години
MARKET_UPDATE_COOLDOWN = 4 * 3600 # 4 години

def get_market_info():
    conn = sqlite3.connect('percy_jackson_bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT item_id, special_offer_price, special_offer_end_time FROM market')
    result = cursor.fetchone()
    conn.close()
    return result

def get_market_items():
    conn = sqlite3.connect('percy_jackson_bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT item_id, item_name, item_price, last_updated FROM market_items_for_sale')
    result = cursor.fetchall()
    conn.close()
    return result

def update_market_offer():
    conn = sqlite3.connect('percy_jackson_bot.db')
    cursor = conn.cursor()
    
    current_time = int(time.time())
    
    cursor.execute('SELECT * FROM market')
    offer_exists = cursor.fetchone()

    if not offer_exists or offer_exists[2] < current_time:
        all_items = [item for activity in LOOT_ITEMS.values() for rarity in activity.values() for item in rarity]
        if all_items:
            random_item = random.choice(all_items)
            special_price = round(random_item['value'] * 1.1)
            end_time = current_time + SPECIAL_OFFER_DURATION
            
            cursor.execute('INSERT OR REPLACE INTO market (item_id, special_offer_price, special_offer_end_time) VALUES (?, ?, ?)',
                           (random_item['id'].strip(), special_price, end_time))
            conn.commit()
    conn.close()

def update_market_items():
    conn = sqlite3.connect('percy_jackson_bot.db')
    cursor = conn.cursor()
    
    current_time = int(time.time())
    
    cursor.execute('SELECT last_updated FROM market_items_for_sale LIMIT 1')
    last_updated_time = cursor.fetchone()
    
    if not last_updated_time or (current_time - last_updated_time[0]) > MARKET_UPDATE_COOLDOWN:
        cursor.execute('DELETE FROM market_items_for_sale')
        
        all_items = [item for activity in LOOT_ITEMS.values() for rarity in activity.values() for item in rarity]
        random_items = random.sample(all_items, k=5)
        
        for item in random_items:
            cursor.execute('INSERT INTO market_items_for_sale (item_id, item_name, item_price, last_updated) VALUES (?, ?, ?, ?)',
                           (item['id'].strip(), item['name'], item['value'], current_time))
        conn.commit()
    conn.close()

def sell_item_on_market_logic(user_id, item_id, quantity=1, special_offer=False):
    item_quantity = get_item_quantity_in_inventory(user_id, item_id.strip())
    
    if item_quantity < quantity:
        return None
    
    item_info = get_item_info(item_id.strip())
    if not item_info:
        return None

    if special_offer:
        market_info = get_market_info()
        if market_info and market_info[0].strip() == item_id.strip() and market_info[2] > time.time():
            sale_price = market_info[1]
        else:
            return None
    else:
        sale_price = int(item_info['value'] * 0.85)

    total_sale_value = int(sale_price * quantity)
    add_drachmas_to_user(user_id, total_sale_value)
    
    remove_item_from_inventory(user_id, item_id.strip(), quantity)
    
    return total_sale_value

def buy_item_from_market_logic(user_id, item_id, quantity=1):
    drachmas = get_user_drachmas(user_id)
    item_info = get_item_info(item_id.strip())
    
    if not item_info:
        return {'status': 'error', 'message': 'Цей предмет не знайдено.'}

    price = item_info['value'] * quantity
    if drachmas < price:
        return {'status': 'error', 'message': 'У вас недостатньо драхм.'}

    add_item_to_inventory(user_id, item_id.strip(), quantity)

    conn = sqlite3.connect('percy_jackson_bot.db')
    cursor = conn.cursor()
    new_drachmas = drachmas - price
    cursor.execute('UPDATE users SET drachmas = ? WHERE user_id = ?', (new_drachmas, user_id))
    conn.commit()
    conn.close()
    
    return {'status': 'success', 'message': f"Ви купили **{item_info['name']}** за {price} драхм."}

def show_market(message, bot):
    update_market_offer()
    
    market_text = "🏛 **Ринок магічних артефактів**\n"
    market_text += "В цей ясний день ви вибрались на маркет. Навколо ви бачите не так вже й багато істот, але розумієте що саме тут зможете продати все накоплене, або знайти те, що вам необхідно для майбутніх подорожей."
    
    markup = InlineKeyboardMarkup()
    
    # ------------------ Спеціальна пропозиція ------------------
    market_info = get_market_info()
    if market_info:
        item_id, special_price, end_time = market_info
        item_info = get_item_info(item_id.strip())
        if item_info and end_time > time.time():
            # Додаємо текст про спец. пропозицію
            market_text += f"\n\n🔥 **СПЕЦІАЛЬНА ПРОПОЗИЦІЯ!**\n"
            
            # Розрахунок часу, що залишився
            time_left = end_time - time.time()
            hours_left = int(time_left // 3600)
            minutes_left = int((time_left % 3600) // 60)
            
            market_text += f"Сьогодні **{item_info['name']}** можна продати за **{int(special_price)} драхм** за одиницю!\n"
            market_text += f"Акція закінчиться через: {hours_left} год {minutes_left} хв."
            
            # Додаємо кнопку продажу за акційною ціною
            markup.add(InlineKeyboardButton(f"💰 Продати {item_info['name']} по акції", callback_data=f'sell_special_{item_id.strip()}'))

    # ------------------ Загальні кнопки "Купити" та "Продати" ------------------
    # Ці кнопки відкриватимуть інший "шар" інтерфейсу, як на скріншоті
    markup.add(
        InlineKeyboardButton("🛒 Купити", callback_data='show_buy_menu'),
        InlineKeyboardButton("💰 Продати", callback_data='show_sell_menu')
    )
    
    bot.send_message(message.chat.id, market_text, parse_mode='Markdown', reply_markup=markup)

def show_buy_menu(call, bot):
    update_market_items()
    market_items = get_market_items()
    markup = InlineKeyboardMarkup()
    
    if market_items:
        for item_id, item_name, item_price, _ in market_items:
            markup.add(InlineKeyboardButton(f"Купити {item_name} ({item_price} драхм)", callback_data=f'buy_{item_id.strip()}'))
            
    markup.add(InlineKeyboardButton("⬅️ Назад", callback_data='back_to_market'))

    bot.edit_message_text("🛍️ **Товари на ринку:**\n\nВи можете придбати наступні артефакти:",
                          call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='Markdown')

def show_sell_menu(call, bot):
    user_id = call.from_user.id
    user_inventory = get_user_inventory(user_id)
    markup = InlineKeyboardMarkup()
    
    if user_inventory:
        for item_id, quantity in user_inventory:
            item_info = get_item_info(item_id.strip())
            if item_info:
                sell_price = int(item_info['value'] * 0.85)
                markup.add(InlineKeyboardButton(f"Продати {item_info['name']} (x{quantity}) за {sell_price} драхм", callback_data=f'sell_{item_id.strip()}'))

    markup.add(InlineKeyboardButton("⬅️ Назад", callback_data='back_to_market'))

    bot.edit_message_text("💰 **Ваш інвентар для продажу:**\n\nОберіть предмет, який хочете продати:",
                          call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='Markdown')

def sell_item_callback(call, bot):
    user_id = call.from_user.id
    item_id = call.data.replace('sell_', '').strip()
    special_offer = False

    # Перевірка, чи це спеціальна пропозиція
    if call.data.startswith('sell_special_'):
        item_id = call.data.replace('sell_special_', '').strip()
        special_offer = True

    equipped_item_id = get_user_equipped_item(user_id)
    if equipped_item_id == item_id:
        equipped_item_name = get_item_info(equipped_item_id)['name']
        bot.answer_callback_query(call.id, f"❌ Спочатку зніміть екіпірований предмет ({equipped_item_name}), щоб його продати.", show_alert=True)
        return

    item_quantity = get_item_quantity_in_inventory(user_id, item_id)
    if item_quantity < 1:
        bot.answer_callback_query(call.id, "У вас немає цього предмета в інвентарі.", show_alert=True)
        return

    result = sell_item_on_market_logic(user_id, item_id, special_offer=special_offer)
    if result is not None:
        item_info = get_item_info(item_id)
        bot.answer_callback_query(call.id, f"✅ Ви продали {item_info['name']} за {result} драхм.")
        # Повертаємо користувача до головного меню після продажу
        show_market(call.message, bot)
    else:
        bot.answer_callback_query(call.id, "❌ Неможливо продати цей предмет за цією пропозицією.", show_alert=True)

def buy_item_callback(call, bot):
    user_id = call.from_user.id
    item_id = call.data.replace('buy_', '').strip()
    
    item_info = get_item_info(item_id.strip())
    if not item_info:
        bot.answer_callback_query(call.id, "Цей предмет не знайдено на ринку.", show_alert=True)
        return

    result = buy_item_from_market_logic(user_id, item_id.strip())
    
    if result['status'] == 'success':
        bot.answer_callback_query(call.id, result['message'], show_alert=True)
        # Повертаємо користувача до меню купівлі
        show_buy_menu(call, bot)
    else:
        bot.answer_callback_query(call.id, result['message'], show_alert=True)

def register_market_handlers(bot):
    bot.message_handler(commands=['market'])(lambda m: show_market(m, bot))
    bot.callback_query_handler(func=lambda call: call.data == 'show_buy_menu')(lambda c: show_buy_menu(c, bot))
    bot.callback_query_handler(func=lambda call: call.data == 'show_sell_menu')(lambda c: show_sell_menu(c, bot))
    bot.callback_query_handler(func=lambda call: call.data == 'back_to_market')(lambda c: show_market(c.message, bot))
    bot.callback_query_handler(func=lambda call: call.data.startswith('buy_'))(lambda c: buy_item_callback(c, bot))
    bot.callback_query_handler(func=lambda call: call.data.startswith('sell_'))(lambda c: sell_item_callback(c, bot))
    bot.callback_query_handler(func=lambda call: call.data.startswith('sell_special_'))(lambda c: sell_item_callback(c, bot))