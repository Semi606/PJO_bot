import telebot
import random
import sqlite3
import time
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from loot_items import get_random_loot
from db_utils import get_user_energy, set_user_energy, add_item_to_inventory, get_user_profile, increment_user_strength, get_user_strength, get_item_quantity_in_inventory, remove_item_from_inventory

def _get_activity_display_and_markup(user_id):
    energy = get_user_energy(user_id)
    if energy is None:
        return None, None
        
    strength = get_user_strength(user_id)
    
    activity_text = f"🏹 Виберіть активність. Ваша енергія: {energy}/15"
    
    if energy < 15:
        conn = sqlite3.connect('percy_jackson_bot.db')
        cursor = conn.cursor()
        cursor.execute('SELECT last_energy_restore_time FROM users WHERE user_id = ?', (user_id,))
        last_time_result = cursor.fetchone()
        last_time = last_time_result[0] if last_time_result else 0
        conn.close()

        time_left = 1800 - (int(time.time()) - last_time) % 1800
        minutes = int(time_left // 60)
        seconds = int(time_left % 60)
        activity_text += f"\n_Енергія відновиться через: {minutes} хв {seconds} с_"
    
    activity_text += f"\n\n💪 Ваша сила: {strength}"
    
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("Полювання (1 енергія)", callback_data='activity_hunt'),
        InlineKeyboardButton("Риболовля (1 енергія)", callback_data='activity_fish')
    )
    markup.add(
        InlineKeyboardButton("Тренування (1 енергія)", callback_data='activity_workout')
    )
    
    return activity_text, markup

# Обробник команди /activity
def show_activities(message, bot):
    user_id = message.from_user.id
    activity_text, markup = _get_activity_display_and_markup(user_id)
    
    if activity_text is None:
        bot.send_message(message.chat.id, "Схоже, у вас ще немає профілю. Використайте /create, щоб його створити.")
        return

    bot.send_message(message.chat.id, activity_text, reply_markup=markup, parse_mode='Markdown')

# Обробник callback-запитів від кнопок активності
def handle_activity_callback(call, bot):
    user_id = call.from_user.id
    activity_type = call.data.replace('activity_', '')
    energy = get_user_energy(user_id)
    
    if energy is None or energy < 1:
        bot.answer_callback_query(call.id, "У вас недостатньо енергії для цієї активності!", show_alert=True)
        return
    
    set_user_energy(user_id, energy - 1)
    
    if activity_type == 'workout':
        increment_user_strength(user_id)
        bot.answer_callback_query(call.id, "Ви потренувалися та стали сильнішими!", show_alert=True)
        
    elif activity_type in ['hunt', 'fish']:
        item_info = get_random_loot(activity_type)
        
        if item_info:
            item_id = item_info['id']
            item_name = item_info['name']
            add_item_to_inventory(user_id, item_id)
            bot.answer_callback_query(call.id, f"🎉 Ви знайшли {item_name}!", show_alert=True)
        else:
            bot.answer_callback_query(call.id, "😔 Ви нічого не знайшли...", show_alert=True)
    
    # Оновлення вікна активності
    activity_text, markup = _get_activity_display_and_markup(user_id)
    if activity_text:
        bot.edit_message_text(activity_text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='Markdown')

# Функція для реєстрації обробників
def register_activity_handlers(bot):
    bot.message_handler(commands=['activity'])(lambda m: show_activities(m, bot))
    bot.callback_query_handler(func=lambda call: call.data.startswith('activity_'))(lambda c: handle_activity_callback(c, bot))