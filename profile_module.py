import telebot
import sqlite3
import time
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from db_utils import save_user_profile, get_user_profile, get_user_drachmas, get_user_energy, get_user_strength, get_user_equipped_item
from loot_items import get_item_info

# Список богів для кнопок і маппінг до номерів кабін
GODS_LIST = [
    "Зевс", "Гера", "Посейдон", "Деметра", "Арес", "Афіна", "Аполлон", "Артеміда",
    "Гефест", "Афродіта", "Гермес", "Діоніс", "Аїд", "Іріс", "Гіпнос",
    "Немезіда", "Найк", "Геба", "Тіхе", "Геката"
]
GODS_TO_CABIN = {god: index + 1 for index, god in enumerate(GODS_LIST)}
    
# Обробник для нових учасників
def handle_new_member(message, bot):
    for user in message.new_chat_members:
        save_user_profile(user.id, user.first_name)
        
        username = user.first_name
        welcome_message = (
            f"Привіт, {username}! Вітаємо в чаті фанатів 'Персі Джексона'. "
            "Розкрий нам таємницю - якого бога ти дитина? "
            "Якщо не знаєш - не біда. Це можна дізнатися за посиланням: "
            "https://www.percyjacksongetclaimed.com/p/global"
        )
        bot.send_message(message.chat.id, welcome_message)

# Обробник команди /create для існуючих користувачів
def create_profile(message, bot):
    user_id = message.from_user.id
    username = message.from_user.first_name
    
    profile = get_user_profile(user_id)
    if not profile:
        save_user_profile(user_id, username)
        bot.send_message(message.chat.id, "✅ Ваш профіль успішно створено. Тепер ви можете його відредагувати командою /edit.")
    else:
        bot.send_message(message.chat.id, "У вас вже є профіль.")

# Обробник команди /profile
def show_profile(message, bot):
    user_id = message.from_user.id
    profile = get_user_profile(user_id)
    
    if profile:
        _, username, parent, pronouns, drachmas, energy, _, strength, health, defense, equipped_item, last_energy_restore_time = profile
        
        parent_info = parent if parent else "не вказано"
        
        cabin_number_str = GODS_TO_CABIN.get(parent, 'не вказано')
        if isinstance(cabin_number_str, int):
            cabin_number_str = f"Кабіна {cabin_number_str}"
        
        pronouns_info = pronouns if pronouns else "не вказано"
        
        energy_status = f"⚡ **Енергія:** {energy}/15"
        if energy < 15:
            time_left = 1800 - (int(time.time()) - last_energy_restore_time) % 1800
            minutes = int(time_left // 60)
            seconds = int(time_left % 60)
            energy_status += f" (відновлення через {minutes} хв {seconds} с)"
        
        equipped_item_name = "немає"
        equipped_item_bonus = 0
        if equipped_item:
            item_info = get_item_info(equipped_item)
            if item_info and item_info.get('type') == 'weapon':
                equipped_item_name = item_info['name']
                equipped_item_bonus = item_info['strength_bonus']
        
        final_strength = strength + equipped_item_bonus

        profile_message = (
            f"**Профіль користувача {username}**\n\n"
            f"👤 **Ім'я:** {username}\n"
            f"🗣 **Займенники:** {pronouns_info}\n"
            f"🏛 **Дитина бога:** {parent_info}\n"
            f"🏠 **Будинок:** {cabin_number_str}\n"
            f"💰 **Гаманець:** {drachmas} драхм\n"
            f"{energy_status}\n"
            f"❤️ **Здоров'я:** {health}\n"
            f"🛡 **Захист:** {defense}\n"
            f"💪 **Сила:** {final_strength} (базова: {strength})\n"
            f"⚔️ **Екіпіровано:** {equipped_item_name}"
        )
        bot.send_message(message.chat.id, profile_message, parse_mode='Markdown')
    else:
        bot.send_message(message.chat.id, "Ваш профіль не знайдено. Скористайтеся командою /create.")

# Функція для створення кнопок з богами
def gen_gods_markup():
    markup = InlineKeyboardMarkup()
    markup.row_width = 2
    
    buttons = [InlineKeyboardButton(god, callback_data=f"set_god_{god}") for god in GODS_LIST]
    markup.add(*buttons)
    return markup

# Обробник команди /edit
def start_edit_profile(message, bot):
    user_id = message.from_user.id
    
    if message.chat.type != "private":
        bot.send_message(message.chat.id, "✏️ Редагувати профіль можна тільки в приватних повідомленнях з ботом.")
        return
    
    bot.send_message(
        user_id, 
        "✏️ **Редагування профілю**\n\n"
        "Оберіть бога, чиєю дитиною ви є, натиснувши на кнопку нижче. "
        "Для редагування інших даних (ім'я, займенники), надішліть повідомлення у форматі:\n"
        "`Ім'я: Ваше нове ім'я`\n"
        "`Займенники: Ваші займенники`",
        parse_mode='Markdown'
    )
    
    bot.send_message(user_id, "Оберіть свого бога:", reply_markup=gen_gods_markup())

# Обробник callback-запитів від кнопок
def callback_set_god(call, bot):
    user_id = call.from_user.id
    username = call.from_user.first_name
    
    god = call.data.replace('set_god_', '')
    
    save_user_profile(user_id, username, parent=god)
    
    bot.answer_callback_query(call.id, f"✅ Ви обрали: {god}. Ваш профіль оновлено!")
    
    cabin_number_str = GODS_TO_CABIN.get(god, 'не вказано')
    if isinstance(cabin_number_str, int):
        cabin_number_str = f"Кабіна {cabin_number_str}"

    bot.send_message(call.message.chat.id, f"✅ Профіль оновлено! Ваш будинок: **{cabin_number_str}**", parse_mode='Markdown')

# Обробник текстових повідомлень для редагування інших полів
def edit_other_profile_fields(message, bot):
    user_id = message.from_user.id
    text = message.text
    
    current_profile = get_user_profile(user_id)
    if not current_profile:
        bot.send_message(user_id, "Спочатку скористайтеся командою /create, щоб створити профіль.")
        return
        
    _, current_username, current_parent, current_pronouns, _, _, _, _, _, _, _, _ = current_profile
    
    lines = text.split('\n')
    new_data = {}
    for line in lines:
        try:
            key, value = line.split(':', 1)
            new_data[key.strip()] = value.strip()
        except ValueError:
            pass
            
    new_username = new_data.get("Ім'я", current_username)
    new_pronouns = new_data.get("Займенники", current_pronouns)
    
    save_user_profile(user_id, new_username, parent=current_parent, pronouns=new_pronouns)
    
    bot.send_message(user_id, "✅ Ваш профіль успішно оновлено!")
    
# Функція для реєстрації всіх обробників
def register_profile_handlers(bot):
    bot.message_handler(content_types=['new_chat_members'])(lambda m: handle_new_member(m, bot))
    bot.message_handler(commands=['create'])(lambda m: create_profile(m, bot))
    bot.message_handler(commands=['profile'])(lambda m: show_profile(m, bot))
    bot.message_handler(commands=['edit'])(lambda m: start_edit_profile(m, bot))
    bot.callback_query_handler(func=lambda call: call.data.startswith('set_god_'))(lambda c: callback_set_god(c, bot))
    bot.message_handler(func=lambda message: message.text and ("Ім'я:" in message.text or "Займенники:" in message.text) and message.chat.type == "private")(lambda m: edit_other_profile_fields(m, bot))