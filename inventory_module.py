import telebot
import sqlite3
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from loot_items import get_item_info
from db_utils import add_drachmas_to_user, get_user_inventory, clear_inventory, remove_item_from_inventory, get_user_energy, set_user_energy, get_item_quantity_in_inventory, equip_item, unequip_item, get_user_equipped_item

def _get_inventory_display_and_markup(user_id):
    items = get_user_inventory(user_id)
    equipped_item_id = get_user_equipped_item(user_id)
    
    inventory_text = "🎒 **Ваш інвентар:**\n"
    markup = InlineKeyboardMarkup()
    
    if not items:
        inventory_text += "\n_Інвентар порожній._"
    else:
        for item_id, quantity in items:
            item_info = get_item_info(item_id)
            if item_info:
                item_name = item_info['name']
                item_value = int(item_info['value'] * 0.5)
                
                is_equipped = (item_id == equipped_item_id)
                equipped_text = " (Екіпіровано)" if is_equipped else ""
                
                inventory_text += f"\n▪️ **{item_name}** (x{quantity}){equipped_text}\n"
                
                if item_info.get('type') == 'weapon':
                    if is_equipped:
                        markup.add(InlineKeyboardButton(f"🚫 Зняти {item_name}", callback_data=f'unequip_item_{item_id}'))
                    else:
                        markup.add(InlineKeyboardButton(f"⚔️ Одягти {item_name}", callback_data=f'equip_item_{item_id}'))
                elif 'potion' in item_id:
                    markup.add(InlineKeyboardButton(f"🧪 Використати {item_name}", callback_data=f'use_item_{item_id}'))
                else:
                    markup.add(InlineKeyboardButton(f"💰 Продати {item_name} ({item_value} драхм)", callback_data=f'sell_item_{item_id}'))
        
        markup.add(InlineKeyboardButton("💰 Продати все (50% ціни)", callback_data='sell_all_items'))

    return inventory_text, markup

# Обробник команди /inventory
def show_inventory(message, bot):
    user_id = message.from_user.id
    inventory_text, markup = _get_inventory_display_and_markup(user_id)
    bot.send_message(message.chat.id, inventory_text, parse_mode='Markdown', reply_markup=markup)

# Обробник кнопки "Одягти"
def equip_item_callback(call, bot):
    user_id = call.from_user.id
    item_id = call.data.replace('equip_item_', '')
    
    item_quantity = get_item_quantity_in_inventory(user_id, item_id)
    if item_quantity < 1:
        bot.answer_callback_query(call.id, "У вас немає цього предмета в інвентарі.", show_alert=True)
        return
        
    equipped_item_id = get_user_equipped_item(user_id)
    if equipped_item_id and equipped_item_id != item_id:
        bot.answer_callback_query(call.id, "У вас уже екіпірований інший предмет. Зніміть його спочатку.", show_alert=True)
        return

    equip_item(user_id, item_id)
    bot.answer_callback_query(call.id, f"✅ Ви одягнули {get_item_info(item_id)['name']}!")
    
    inventory_text, markup = _get_inventory_display_and_markup(user_id)
    bot.edit_message_text(inventory_text, call.message.chat.id, call.message.message_id, parse_mode='Markdown', reply_markup=markup)

# Обробник кнопки "Зняти"
def unequip_item_callback(call, bot):
    user_id = call.from_user.id
    item_id = call.data.replace('unequip_item_', '')
    
    equipped_item_id = get_user_equipped_item(user_id)
    if equipped_item_id != item_id:
        bot.answer_callback_query(call.id, "Цей предмет не екіпірований.", show_alert=True)
        return
        
    unequip_item(user_id)
    bot.answer_callback_query(call.id, f"✅ Ви зняли {get_item_info(item_id)['name']}!")
    
    inventory_text, markup = _get_inventory_display_and_markup(user_id)
    bot.edit_message_text(inventory_text, call.message.chat.id, call.message.message_id, parse_mode='Markdown', reply_markup=markup)

# Обробник кнопки "Використати"
def use_item_callback(call, bot):
    user_id = call.from_user.id
    item_id = call.data.replace('use_item_', '')
    
    item_info = get_item_info(item_id)
    if not item_info:
        bot.answer_callback_query(call.id, "Цей предмет не знайдено.")
        return

    item_quantity = get_item_quantity_in_inventory(user_id, item_id)
    
    if item_quantity < 1:
        bot.answer_callback_query(call.id, "У вас немає цього предмета в інвентарі.", show_alert=True)
        return

    current_energy = get_user_energy(user_id)
    max_energy = 15
        
    if current_energy >= max_energy:
        bot.answer_callback_query(call.id, "У вас повна енергія!", show_alert=True)
        return

    energy_to_restore = 0
    if item_id == 'small_potion':
        energy_to_restore = 5
    elif item_id == 'medium_potion':
        energy_to_restore = 10
    elif item_id == 'big_potion':
        energy_to_restore = 15

    new_energy = min(current_energy + energy_to_restore, max_energy)
    set_user_energy(user_id, new_energy)
    remove_item_from_inventory(user_id, item_id)
    
    bot.answer_callback_query(call.id, f"✅ Ви використали {item_info['name']}. Відновлено {new_energy - current_energy} енергії.", show_alert=True)
    
    inventory_text, markup = _get_inventory_display_and_markup(user_id)
    bot.edit_message_text(inventory_text, call.message.chat.id, call.message.message_id, parse_mode='Markdown', reply_markup=markup)

# Обробник кнопки "Продати все"
def sell_all_items_callback(call, bot):
    user_id = call.from_user.id
    items = get_user_inventory(user_id)
    equipped_item_id = get_user_equipped_item(user_id)
    
    if not items:
        bot.answer_callback_query(call.id, "Інвентар уже порожній.")
        return
    
    # Перевірка на наявність екіпірованих предметів
    if equipped_item_id:
        equipped_item_name = get_item_info(equipped_item_id)['name']
        bot.answer_callback_query(call.id, f"❌ Спочатку зніміть екіпірований предмет ({equipped_item_name}), щоб продати все.", show_alert=True)
        return
    
    total_sale_value = 0
    for item_id, quantity in items:
        item_info = get_item_info(item_id)
        if item_info:
            total_sale_value += (item_info['value'] * quantity * 0.5)
            
    add_drachmas_to_user(user_id, int(total_sale_value))
    clear_inventory(user_id)
    
    bot.answer_callback_query(call.id, f"✅ Ви продали весь інвентар за {int(total_sale_value)} драхм!")
    
    inventory_text, markup = _get_inventory_display_and_markup(user_id)
    bot.edit_message_text(inventory_text, call.message.chat.id, call.message.message_id, parse_mode='Markdown', reply_markup=markup)

# Обробник кнопки продажу окремого предмета
def sell_single_item_callback(call, bot):
    user_id = call.from_user.id
    item_id = call.data.replace('sell_item_', '')
    
    equipped_item_id = get_user_equipped_item(user_id)
    if equipped_item_id == item_id:
        equipped_item_name = get_item_info(equipped_item_id)['name']
        bot.answer_callback_query(call.id, f"❌ Спочатку зніміть екіпірований предмет ({equipped_item_name}), щоб його продати.", show_alert=True)
        return

    item_quantity = get_item_quantity_in_inventory(user_id, item_id)
    
    if item_quantity < 1:
        bot.answer_callback_query(call.id, "У вас немає цього предмета в інвентарі.", show_alert=True)
        return
        
    item_info = get_item_info(item_id)
    item_value = int(item_info['value'] * 0.5)
    
    remove_item_from_inventory(user_id, item_id)
    add_drachmas_to_user(user_id, item_value)
    
    bot.answer_callback_query(call.id, f"✅ Ви продали {item_info['name']} за {item_value} драхм.")
    
    inventory_text, markup = _get_inventory_display_and_markup(user_id)
    bot.edit_message_text(inventory_text, call.message.chat.id, call.message.message_id, parse_mode='Markdown', reply_markup=markup)

def register_inventory_handlers(bot):
    bot.message_handler(commands=['inventory'])(lambda m: show_inventory(m, bot))
    bot.callback_query_handler(func=lambda call: call.data == 'sell_all_items')(lambda c: sell_all_items_callback(c, bot))
    bot.callback_query_handler(func=lambda call: call.data.startswith('sell_item_'))(lambda c: sell_single_item_callback(c, bot))
    bot.callback_query_handler(func=lambda call: call.data.startswith('use_item_'))(lambda c: use_item_callback(c, bot))
    bot.callback_query_handler(func=lambda call: call.data.startswith('equip_item_'))(lambda c: equip_item_callback(c, bot))
    bot.callback_query_handler(func=lambda call: call.data.startswith('unequip_item_'))(lambda c: unequip_item_callback(c, bot))