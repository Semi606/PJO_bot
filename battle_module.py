import sqlite3
import telebot
import random
import time
import threading
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from db_utils import get_user_profile, get_user_drachmas, get_user_strength, get_user_equipped_item, add_item_to_inventory, get_item_quantity_in_inventory, create_raid_db, add_raid_participant_db, get_raid_participants_db, get_active_raid_info, remove_item_from_inventory, update_raid_status_db, get_raid_participants_with_damage_db, update_raid_participant_damage_db, end_raid_db, add_drachmas_to_user, get_all_users, get_random_inventory_item # <-- Додано імпорт
from monsters import MONSTERS
from loot_items import LOOT_ITEMS, get_item_info, get_random_loot

RAID_COOLDOWN = 24 * 3600  # 24 години
RAID_SETUP_DURATION = 30 * 60  # 30 хвилин
RAID_UPDATE_INTERVAL = 10  # 10 секунд

# --- ГЛОБАЛЬНІ СТРУКТУРИ ДЛЯ ДУЕЛЕЙ ---
active_duels = {}
duel_messages = {}

# --- ДОПОМІЖНІ ФУНКЦІЇ ДЛЯ ДУЕЛЕЙ ---
def calculate_damage(attacker_id, equipped_item_id):
    strength = get_user_strength(attacker_id)
    if equipped_item_id:
        item_info = get_item_info(equipped_item_id)
        if item_info and item_info.get('type') == 'weapon':
            strength += item_info['strength_bonus']
    return random.randint(int(strength * 0.8), int(strength * 1.2))

def start_duel(message, bot):
    if not message.reply_to_message:
        bot.send_message(message.chat.id, "❌ Щоб викликати когось на дуель, дайте відповідь на його повідомлення командою /duel.")
        return

    challenger_id = message.from_user.id
    opponent_id = message.reply_to_message.from_user.id
    
    if challenger_id == opponent_id:
        bot.send_message(message.chat.id, "❌ Ви не можете викликати на дуель самого себе.")
        return

    challenger_profile = get_user_profile(challenger_id)
    opponent_profile = get_user_profile(opponent_id)

    if not challenger_profile:
        bot.send_message(message.chat.id, f"❌ {message.from_user.first_name}, ви не можете битися без профілю! Створіть його командою /create.")
        return
    if not opponent_profile:
        bot.send_message(message.chat.id, f"❌ {message.reply_to_message.from_user.first_name} не має профілю і не може брати участь у дуелі.")
        return

    challenger_name = message.from_user.first_name
    opponent_name = message.reply_to_message.from_user.first_name

    challenger_strength = challenger_profile[7]
    opponent_strength = opponent_profile[7]
    
    equipped_item_challenger = challenger_profile[10]
    equipped_item_opponent = opponent_profile[10]

    if equipped_item_challenger:
        item_info = get_item_info(equipped_item_challenger)
        if item_info and item_info.get('type') == 'weapon':
            challenger_strength += item_info['strength_bonus']
    
    if equipped_item_opponent:
        item_info = get_item_info(equipped_item_opponent)
        if item_info and item_info.get('type') == 'weapon':
            opponent_strength += item_info['strength_bonus']

    total_strength = challenger_strength + opponent_strength
    challenger_win_chance = (challenger_strength / total_strength) * 100

    roll = random.uniform(0, 100)

    if roll <= challenger_win_chance:
        winner_id, winner_name = challenger_id, challenger_name
        loser_id, loser_name = opponent_id, opponent_name
    else:
        winner_id, winner_name = opponent_id, opponent_name
        loser_id, loser_name = challenger_id, challenger_name

    loser_drachmas = get_user_drachmas(loser_id)
    if loser_drachmas is None: loser_drachmas = 0

    if loser_drachmas > 0:
        prize_amount = int(loser_drachmas * 0.25)
        if prize_amount < 1: prize_amount = 1
        
        add_drachmas_to_user(winner_id, prize_amount)
        add_drachmas_to_user(loser_id, -prize_amount)
        
        message_text = (
            f"⚔️ **ДУЕЛЬ!**\n\n"
            f"**{challenger_name}** (сила: {challenger_strength:.1f}) викликає на поєдинок **{opponent_name}** (сила: {opponent_strength:.1f})!\n"
            f"Після запеклого бою перемагає **{winner_name}**!"
            f"Він забирає у переможеного **{prize_amount}** драхм."
        )
    else:
        stolen_item = get_random_inventory_item(loser_id)
        if stolen_item:
            stolen_item_info = get_item_info(stolen_item)
            if stolen_item_info:
                stolen_item_name = stolen_item_info['name']
                remove_item_from_inventory(loser_id, stolen_item)
                add_item_to_inventory(winner_id, stolen_item)
                message_text = (
                    f"⚔️ **ДУЕЛЬ!**\n\n"
                    f"**{challenger_name}** (сила: {challenger_strength:.1f}) викликає на поєдинок **{opponent_name}** (сила: {opponent_strength:.1f})!\n"
                    f"Перемагає **{winner_name}**!"
                    f"Оскільки у **{loser_name}** не було драхм, переможець забирає його предмет: **{stolen_item_name}**."
                )
            else:
                message_text = (
                    f"⚔️ **ДУЕЛЬ!**\n\n"
                    f"**{challenger_name}** (сила: {challenger_strength:.1f}) викликає на поєдинок **{opponent_name}** (сила: {opponent_strength:.1f})!\n"
                    f"Перемагає **{winner_name}**!\n"
                    f"Але у **{loser_name}** немає ні драхм, ні предметів... "
                    f"Поєдинок закінчується без призу."
                )
        else:
            message_text = (
                f"⚔️ **ДУЕЛЬ!**\n\n"
                f"**{challenger_name}** (сила: {challenger_strength:.1f}) викликає на поєдинок **{opponent_name}** (сила: {opponent_strength:.1f})!\n"
                f"Перемагає **{winner_name}**!\n"
                f"Але у **{loser_name}** немає ні драхм, ні предметів... "
                f"Поєдинок закінчується без призу."
            )

    bot.send_message(message.chat.id, message_text, parse_mode='Markdown')

# --- ФУНКЦІОНАЛ РЕЙДІВ ---
def get_random_raid_monsters():
    conn = sqlite3.connect('percy_jackson_bot.db')
    cursor = conn.cursor()
    
    current_time = int(time.time())
    
    cursor.execute('SELECT item_id, special_offer_end_time FROM market WHERE special_offer_price IS NOT NULL')
    result = cursor.fetchone()
    
    if not result or result[1] < current_time:
        random_monsters = random.sample(MONSTERS, k=4)
        
        cursor.execute('DELETE FROM market WHERE special_offer_price IS NOT NULL')
        for monster in random_monsters:
            cursor.execute('INSERT OR REPLACE INTO market (item_id, special_offer_price, special_offer_end_time) VALUES (?, ?, ?)',
                           (monster['id'], monster['health'], current_time + RAID_COOLDOWN))
        conn.commit()
    
    cursor.execute('SELECT item_id FROM market WHERE special_offer_price IS NOT NULL')
    monster_ids = [row[0] for row in cursor.fetchall()]
    
    conn.close()
    return [m for m in MONSTERS if m['id'] in monster_ids]

def show_raids(message, bot):
    monsters = get_random_raid_monsters()
    
    raid_text = "⚔️ **Доступні Рейди:**\n\n"
    markup = InlineKeyboardMarkup()
    
    for monster in monsters:
        min_players, max_players = monster['required_players']
        raid_text += f"**{monster['name']}**\n"
        raid_text += f"  ❤️ Здоров'я: {monster['health']}\n"
        raid_text += f"  💪 Сила атаки: {monster['damage']}\n"
        raid_text += f"  👥 Гравців: {min_players}-{max_players}\n"
        raid_text += f"  🎁 Нагорода: {monster['reward']} лут\n\n"
        
        markup.add(InlineKeyboardButton(f"Напасти на {monster['name']}", callback_data=f'create_raid_{monster["id"]}'))

    bot.send_message(message.chat.id, raid_text, parse_mode='Markdown', reply_markup=markup)

def create_raid_callback(call, bot):
    chat_id = call.message.chat.id
    user_id = call.from_user.id
    username = call.from_user.first_name
    monster_id = call.data.replace('create_raid_', '')
    
    active_raid = get_active_raid_info(chat_id)
    if active_raid:
        bot.answer_callback_query(call.id, "У цьому чаті вже триває або очікується рейд!", show_alert=True)
        return
        
    monster = next((m for m in MONSTERS if m['id'] == monster_id), None)
    if not monster:
        bot.answer_callback_query(call.id, "Вибраного монстра не знайдено.", show_alert=True)
        return

    raid_message = bot.send_message(chat_id, "Ініціалізація рейду...", parse_mode='Markdown')
    raid_id = create_raid_db(monster_id, chat_id, raid_message.message_id)
    add_raid_participant_db(raid_id, user_id, username)
    
    start_time = int(time.time())
    end_time = start_time + RAID_SETUP_DURATION
    
    bot.answer_callback_query(call.id, f"✅ Ви почали рейд на {monster['name']}!")
    
    update_raid_message(raid_id, monster, start_time, end_time, chat_id, raid_message.message_id, bot)

def update_raid_message(raid_id, monster, start_time, end_time, chat_id, message_id, bot):
    participants = get_raid_participants_db(raid_id)
    min_players, _ = monster['required_players']
    
    participants_list = "\n".join([f"▪️ {p[1]}" for p in participants])
    
    time_left = end_time - int(time.time())
    minutes = int(time_left // 60)
    seconds = int(time_left % 60)
    
    if time_left <= 0 or len(participants) >= min_players:
        if len(participants) >= min_players:
            message_text = f"⚔️ **Рейд на {monster['name']} починається!** Команда готова."
        else:
            message_text = f"⚔️ **Рейд на {monster['name']} починається!** Час вийшов, до бою!"

        markup = None
        update_raid_status_db(raid_id, 'in_progress')
        
        bot.edit_message_text(message_text, chat_id, message_id, parse_mode='Markdown', reply_markup=markup)
        
        start_battle(raid_id, monster, chat_id, bot)
        return
        
    else:
        message_text = (
            f"⚔️ **Підготовка до рейду: {monster['name']}**\n\n"
            f"👥 Гравців: {len(participants)}/{min_players}\n"
            f"⏳ Час до початку: {minutes:02d}:{seconds:02d}\n\n"
            f"**Учасники:**\n"
            f"{participants_list}\n"
        )
        
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("➕ Приєднатися", callback_data=f'join_raid_{raid_id}'))
        
        try:
            bot.edit_message_text(message_text, chat_id, message_id, parse_mode='Markdown', reply_markup=markup)
        except telebot.apihelper.ApiException as e:
            if "message is not modified" in str(e):
                pass
            else:
                print(f"Error editing raid message: {e}")
        
        threading.Timer(RAID_UPDATE_INTERVAL, update_raid_message, args=[raid_id, monster, start_time, end_time, chat_id, message_id, bot]).start()

def join_raid_callback(call, bot):
    user_id = call.from_user.id
    username = call.from_user.first_name
    try:
        raid_id = int(call.data.replace('join_raid_', ''))
    except ValueError:
        bot.answer_callback_query(call.id, "Помилка приєднання до рейду.", show_alert=True)
        return
    
    participants = get_raid_participants_db(raid_id)
    if user_id in [p[0] for p in participants]:
        bot.answer_callback_query(call.id, "Ви вже в цьому рейді!", show_alert=True)
        return

    raid_info = get_active_raid_info(call.message.chat.id)
    if not raid_info or raid_info[0] != raid_id or raid_info[2] != 'pending':
        bot.answer_callback_query(call.id, "Цей рейд вже закінчився або ще не почався.", show_alert=True)
        return
        
    add_raid_participant_db(raid_id, user_id, username)
    bot.answer_callback_query(call.id, "✅ Ви приєдналися до рейду!")
    
def start_battle(raid_id, monster, chat_id, bot):
    monster_health = monster['health']
    turns = 0
    
    while monster_health > 0:
        turns += 1
        participants = get_raid_participants_db(raid_id)
        if not participants:
            bot.send_message(chat_id, "❌ Учасників не залишилось. Рейд завершено поразкою.")
            end_raid_db(raid_id)
            return

        total_damage = 0
        for user_id, _ in participants:
            profile = get_user_profile(user_id)
            if profile:
                equipped_item_id = profile[10]
                strength_bonus = 0
                if equipped_item_id:
                    item_info = get_item_info(equipped_item_id)
                    if item_info and item_info.get('type') == 'weapon':
                        strength_bonus = item_info['strength_bonus']
                total_damage += profile[7] + strength_bonus
                
        monster_health -= total_damage
        
        if monster_health <= 0:
            bot.send_message(chat_id, f"🎉 Перемога! Рейд на {monster['name']} завершено за {turns} ходів.")
            
            loot_item = get_random_loot(monster['reward'].lower())
            
            if loot_item:
                loot_item_name = loot_item['name']
                bot.send_message(chat_id, f"🎁 Всі учасники отримують: **{loot_item_name}**!")
                for user_id, _ in participants:
                    add_item_to_inventory(user_id, loot_item['id'])
            
            damage_report = "📊 **Звіт по рейду:**\n"
            final_participants = get_raid_participants_with_damage_db(raid_id)
            for _, username, damage in final_participants:
                damage_report += f"▪️ {username}: отримав {int(damage)} урону.\n"
            bot.send_message(chat_id, damage_report, parse_mode='Markdown')
            
            end_raid_db(raid_id)
            return
            
        else:
            monster_attack = monster['damage']
            damage_per_player = monster_attack / len(participants)
            
            for user_id, _ in participants:
                update_raid_participant_damage_db(raid_id, user_id, damage_per_player)
                
        time.sleep(3)
    end_raid_db(raid_id)

def register_battle_handlers(bot):
    # Обробники для дуелей
    bot.message_handler(commands=['duel'])(lambda m: start_duel(m, bot))

    # Обробники для рейдів
    bot.message_handler(commands=['raids'])(lambda m: show_raids(m, bot))
    bot.callback_query_handler(func=lambda call: call.data.startswith('create_raid_'))(lambda c: create_raid_callback(c, bot))
    bot.callback_query_handler(func=lambda call: call.data.startswith('join_raid_'))(lambda c: join_raid_callback(c, bot))