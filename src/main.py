import telebot
import psycopg2
from telebot import types
import importlib.util
import importlib.machinery
import threading
from modules.manager_role_time import register_manager_role_time_handlers
from notify import run_scheduler
import os
import logging
import time

logging.basicConfig(level=logging.INFO)

states = {}

DEV_ID = int(os.getenv('DEV_ID'))

bot = telebot.TeleBot(os.getenv('TOKEN'))

register_manager_role_time_handlers(bot)

conn = psycopg2.connect(
    host=os.getenv('DB_HOST'),
    database=os.getenv('DB_NAME'),
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD'),
)
cur = conn.cursor()

notification_thread = threading.Thread(target=run_scheduler)
notification_thread.start()

# Реализация hot_update
def reload_module(module_name, module_func=None):
    spec = importlib.util.spec_from_file_location(module_name, f'modules/{module_name}.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return getattr(module, f"{module_func}")

def get_is_manager(user_id):
    cur.execute("""
        SELECT * FROM roles_users
        WHERE is_manager = true
        AND user_id = %s
    """, (user_id,))
    conn.commit()
    result = cur.fetchone()
    return result

def send_to_me(bot, text, user=None):
    if user:
        user_info = f"ID: {user.id}, Username: @{user.username}"
    else:
        user_info = None
    full_text = f"{user_info}: {text}" if user_info else text
    bot.send_message(os.getenv('DEV_ID'), full_text)

def send_to_user(bot, text, user=None, user_id=None, username=None):
    user_info = None
    if user:
        user_info = f"@{user.username}"
    full_text = f"{user_info} {text}" if user_info else text
    bot.send_message(user_id, full_text)

@bot.message_handler(commands = ['start'])
def start(message):
    bot.send_message(message.from_user.id, f"Приветствую вас, {message.from_user.first_name}!")
    bot.send_message(message.from_user.id, "Для начала работы введите команду /register")

@bot.message_handler(commands = ['update'])
def help(message):
    commands = [
        telebot.types.BotCommand('/update', 'Обновить команды'),
        telebot.types.BotCommand('/register', 'Регистрация в системе'),
        telebot.types.BotCommand('/main_menu', 'Главное меню'),
    ]
    bot.set_my_commands(commands)
    bot.reply_to(message, "Команды обновлены! Перезагрузите Telegram для применения изменений")

@bot.message_handler(commands = ['register'])
def register(message):
    try: 
        with conn:
            cur.execute("""
                SELECT *
                FROM roles_users
                WHERE user_id = %s;
            """, (message.from_user.id,))
            conn.commit()
    except Exception as e:
        logging.error(f"Ошибка при выполнении запроса: {e}")
        bot.send_message(message.chat.id, "Произошла ошибка. Попробуйте ещё раз")
        return
    result = cur.fetchone()
    if result:
        markup = types.InlineKeyboardMarkup()
        item1 = types.InlineKeyboardButton("Да", callback_data='change_role')
        item2 = types.InlineKeyboardButton("Нет, продолжить", callback_data='main_menu_handler')
        markup.add(item1, item2)
        bot.send_message(message.chat.id, "Вы уже зарегистрированы, хотите изменить свои права?", reply_markup=markup)
    else:
        markup = types.InlineKeyboardMarkup()
        item1 = types.InlineKeyboardButton("Я начальник группы", callback_data='manager_register')
        item2 = types.InlineKeyboardButton("Я сотрудник", callback_data='employee_register')
        markup.add(item1, item2)
        bot.send_message(message.chat.id, "Выберите роль:", reply_markup=markup)

@bot.callback_query_handler(lambda call: call.data == 'main_menu_handler')
def main_menu_handler(call):
    bot.answer_callback_query(call.id)
    bot.send_message(call.from_user.id, "Выбери \"/main_menu\", чтобы вернуться в главное меню")

@bot.message_handler(commands=['main_menu'])
def main_menu(message):
    cur.execute("""
        SELECT *
        FROM roles_users
        WHERE user_id = %s;
    """, (message.from_user.id,))
    conn.commit()
    result = cur.fetchone()
    if result:
        if get_is_manager(message.from_user.id):
            markup = types.InlineKeyboardMarkup()
            item1 = types.InlineKeyboardButton("Встреча с сотрудником", callback_data='manager_role_time')
            item2 = types.InlineKeyboardButton("Сменить права", callback_data='change_role')
            markup.add(item1)
            markup.add(item2)
        if message.from_user.id == DEV_ID:
            markup = types.InlineKeyboardMarkup()
            item1 = types.InlineKeyboardButton("Добавить права начальника группы", callback_data='add_manager_role_user')
            item2 = types.InlineKeyboardButton("Удалить права начальника группы", callback_data='del_manager_role_user')
            item3 = types.InlineKeyboardButton("Добавить нового сотрудника", callback_data="add_employee_user")
            item4 = types.InlineKeyboardButton("Добавить нового начальника группы", callback_data="add_manager_user")
            item5 = types.InlineKeyboardButton("Удалить пользователя", callback_data="del_user")
            item6 = types.InlineKeyboardButton("Отправить сообщение", callback_data="message_from_dev")
            markup.add(item1)
            markup.add(item2)
            markup.add(item3)
            markup.add(item4)
            markup.add(item5)
            markup.add(item6)
        else:
            markup = types.InlineKeyboardMarkup()
            item1 = types.InlineKeyboardButton("Встреча с руководителем", callback_data='no_manager')
            item2 = types.InlineKeyboardButton("Сменить права", callback_data='change_role')
            markup.add(item1)
            markup.add(item2)
        bot.send_message(message.from_user.id, "Выберите действие?", reply_markup=markup)
    else:
        bot.send_message(message.from_user.id, "Вы ещё не зарегистрированы, введите команду /register")

@bot.callback_query_handler(lambda call: call.data == 'change_role')
def change_role(call):
    bot.answer_callback_query(call.id)
    cur.execute("""
        SELECT is_manager
        FROM roles_users
        WHERE user_id = %s;
    """, (call.from_user.id,))
    conn.commit()
    result = cur.fetchone()
    if result[0] == True:
        markup = types.InlineKeyboardMarkup()
        item1 = types.InlineKeyboardButton("Да, я хочу удалить права", callback_data='employee_add_register')
        item2 = types.InlineKeyboardButton("Нет, продолжить", callback_data='main_menu_handler')
        markup.add(item1)
        markup.add(item2)
        bot.send_message (call.message.chat.id, "Вы уже начальник группы, хотите удалить свои права?", reply_markup=markup)
    else:
        markup = types.InlineKeyboardMarkup()
        item1 = types.InlineKeyboardButton("Да, я хочу добавить права начальника группы", callback_data='manager_add_register')
        item2 = types.InlineKeyboardButton("Нет, продолжить как сотрудник", callback_data='main_menu_handler')
        markup.add(item1)
        markup.add(item2)
        bot.send_message (call.message.chat.id, "Вы сотрудник, хотите добавить права начальника группы?", reply_markup=markup)

@bot.callback_query_handler(lambda call: call.data == 'manager_register')
def handle_yes_manager(call):
    bot.answer_callback_query(call.id)
    send_to_me(bot, "хочет зарегистрироваться как начальник группы", call.from_user)
    send_to_me(bot, f"{call.from_user.username} {call.from_user.id}")
    bot.send_message(call.from_user.id, "Пожалуйста, ожидайте подтверждения")

@bot.callback_query_handler(lambda call: call.data == 'employee_register')
def handle_yes_employee(call):
    bot.answer_callback_query(call.id)
    send_to_me(bot, "хочет зарегистрироваться как сотрудник", call.from_user)
    send_to_me(bot, f"{call.from_user.username} {call.from_user.id}")
    bot.send_message(call.from_user.id, "Пожалуйста, ожидайте подтверждения")

@bot.callback_query_handler(lambda call: call.data == 'manager_add_register')
def manager_add_register(call):
    bot.answer_callback_query(call.id)
    send_to_me(bot, "хочет добавить права начальника группы", call.from_user)
    send_to_me(bot, f"{call.from_user.username}")
    bot.send_message(call.from_user.id, "Пожалуйста, ожидайте подтверждения")

@bot.callback_query_handler(lambda call: call.data == 'employee_add_register')
def employee_add_register(call):
    bot.answer_callback_query(call.id)
    send_to_me(bot, "хочет удалить права начальника группы", call.from_user)
    send_to_me(bot, f"{call.from_user.username}")
    bot.send_message(call.from_user.id, "Пожалуйста, ожидайте подтверждения")

@bot.callback_query_handler(lambda call: call.data == 'no_manager')	
def handle_employee(call):
    bot.answer_callback_query(call.id)
    markup = types.InlineKeyboardMarkup()
    item1 = types.InlineKeyboardButton("Хочу записаться на встречу с руководителем", callback_data='add_emp_time')
    item2 = types.InlineKeyboardButton("Хочу снять запись на встречу", callback_data='del_emp_time')
    markup.add(item1)
    markup.add(item2)
    bot.send_message(call.from_user.id, "Что вы хотите сделать?", reply_markup=markup)

@bot.callback_query_handler(lambda call: call.data == 'add_emp_time')
def handle_employee_time(call):
    bot.answer_callback_query(call.id)
    cur.execute("""
        SELECT username, user_id
        FROM roles_users
        WHERE is_manager = true
    """)
    conn.commit()
    result = cur.fetchall()
    markup = types.InlineKeyboardMarkup()
    for row in result:
        user_str_id = str(row[1])
        item = types.InlineKeyboardButton(row[0], callback_data='add_emp_time_manager_' + user_str_id)
        markup.add(item)
    bot.send_message(call.from_user.id, "Выберите начальника группы:", reply_markup=markup)

@bot.callback_query_handler(lambda call: call.data.startswith('add_emp_time_manager_'))
def add_emp_time_manager(call):
    call.data = call.data.split('_')[-1]
    manager_id = call.data
    bot.answer_callback_query(call.id)
    states[call.from_user.id] = {'is_manager': False, 'is_del': False, 'manager_id': manager_id}
    choice_date = reload_module('choice_date', 'choice_date')
    markup = choice_date(cur, conn, states, call)
    if markup:
        bot.send_message(call.from_user.id, "Выберите дату:", reply_markup=types.InlineKeyboardMarkup(markup))
    else:
        bot.send_message(call.from_user.id, "Нет свободного времени")

@bot.callback_query_handler(lambda call: call.data == 'del_emp_time')
def handle_del_employee_time(call):
    bot.answer_callback_query(call.id)
    states[call.from_user.id] = {'is_manager': False, 'is_del': True}
    choice_date = reload_module('choice_date', 'choice_date')
    markup = choice_date(cur, conn, states, call)
    if markup:
        bot.send_message(call.from_user.id, "Выберите дату:", reply_markup=types.InlineKeyboardMarkup(markup))
    else:
        bot.send_message(call.from_user.id, "Вы никуда не записаны")

@bot.callback_query_handler(lambda call: call.data == 'del_time')
def handle_del_manager_time(call):
    bot.answer_callback_query(call.id)
    states[call.from_user.id] = {'is_manager': True, 'is_del': True}
    choice_date = reload_module('choice_date', 'choice_date')
    markup = choice_date(cur, conn, states, call)
    if markup:
        bot.send_message(call.from_user.id, "Выберите дату:", reply_markup=types.InlineKeyboardMarkup(markup))
    else:
        bot.send_message(call.from_user.id, "Вы не назначили время для встречи")

@bot.callback_query_handler(func=lambda call: call.data.startswith('date_'))
def handle_date_selection(call):
    selected_date = call.data.split('_')[1]
    bot.answer_callback_query(call.id)
    userstates = states.get(call.from_user.id)
    states[call.from_user.id] = {'date': selected_date, 'is_manager': userstates['is_manager'], 'is_del': userstates['is_del']}
    if not states[call.from_user.id]['is_manager'] and not states[call.from_user.id]['is_del']:
        states[call.from_user.id]['manager_id'] = userstates['manager_id']
    choice_time = reload_module('choice_time', 'choice_time')
    markup = choice_time(cur, conn, states, call)
    if markup:
        bot.send_message(call.from_user.id, "Выберите время:", reply_markup=types.InlineKeyboardMarkup(markup))
    else:
        bot.send_message(call.from_user.id, 'Свободное время отсутствует')

@bot.callback_query_handler(lambda call: call.data.startswith('time_'))
def handle_time_selection(call):
    bot.answer_callback_query(call.id)
    time = call.data.split('_')[1]
    mode_time_selection = reload_module('mode_time_selection', 'mode_time_selection')
    mode_time_selection(bot, cur, conn, states, call, time)

@bot.callback_query_handler(lambda call: call.data == 'add_manager_role_user')
def add_manager_role_user(call):
    bot.answer_callback_query(call.id)
    message = bot.send_message(call.from_user.id, "Введите username пользователя:")
    bot.register_next_step_handler(message, add_manager_role_id)

def add_manager_role_id(message):
    cur.execute("""
        UPDATE roles_users
        SET is_manager = true
        WHERE username = %s
    """, (message.text.replace("@", ""),))
    conn.commit()
    bot.send_message(message.from_user.id, "Права начальника группы добавлены для пользователя " + message.text)
    cur.execute("""
        SELECT user_id
        FROM roles_users
        WHERE username = %s
    """, (message.text.replace("@", ""),))
    conn.commit()
    send_to_user(bot, "Вам добавлены права начальника группы, поздравляю!", None, cur.fetchone()[0])

@bot.callback_query_handler(lambda call: call.data == 'del_manager_role_user')
def del_manager_role_user(call):
    bot.answer_callback_query(call.id)
    message = bot.send_message(call.from_user.id, "Введите username пользователя:")
    bot.register_next_step_handler(message, del_manager_role_id)

def del_manager_role_id(message):
    cur.execute("""
        UPDATE roles_users
        SET is_manager = false
        WHERE username = %s
    """, (message.text.replace("@", ""),))
    conn.commit()
    bot.send_message(message.from_user.id, "Права начальника группы удалены для пользователя " + message.text)
    cur.execute("""
        SELECT user_id
        FROM roles_users
        WHERE username = %s
    """, (message.text.replace("@", ""),))
    conn.commit()
    send_to_user(bot, "Вам удалены права начальника группы", None, cur.fetchone()[0])

@bot.callback_query_handler(lambda call: call.data == 'add_employee_user')
def add_employee_user(call):
    bot.answer_callback_query(call.id)
    message = bot.send_message(call.from_user.id, "Введите username и id пользователя через пробел:")
    bot.register_next_step_handler(message, add_employee_id)

def add_employee_id(message):
    user_id = message.text.split()[1]
    username = message.text.split()[0]
    cur.execute("""
        INSERT INTO roles_users (user_id, username)
        VALUES (%s, %s)
        ON CONFLICT (user_id) DO NOTHING
    """, (user_id, username.split('@')[1]))
    conn.commit()
    bot.send_message(message.from_user.id, "Пользователь " + username + " добавлен")
    send_to_user(bot, f"Пользуйтесь на здоровье!", None, user_id)

@bot.callback_query_handler(lambda call: call.data == 'add_manager_user')
def add_manager_user(call):
    bot.answer_callback_query(call.id)
    message = bot.send_message(call.from_user.id, "Введите username и id пользователя через пробел:")
    bot.register_next_step_handler(message, add_manager_role_id)

def add_manager_id(message):
    user_id = message.text.split()[1]
    username = message.text.split()[0]
    cur.execute("""
        INSERT INTO roles_users (user_id, username, is_manager)
        VALUES (%s, %s, true)
        ON CONFLICT (user_id) DO NOTHING
    """, (user_id, username.split('@')[1]))
    conn.commit()
    bot.send_message(message.from_user.id, "Пользователь " + username + " добавлен")
    send_to_user(bot, f"Пользуйтесь на здоровье!", None, user_id)

@bot.callback_query_handler(lambda call: call.data == 'message_from_dev')
def message_from_dev(call):
    bot.answer_callback_query(call.id)
    message = bot.send_message(call.from_user.id, "Введите сообщение для пользователя и id через _:")
    bot.register_next_step_handler(message, send_from_dev)

def send_from_dev(message):
    user_id = message.text.split('_')[1]
    text = message.text.split('_')[0]
    logging.info(f"Отправляю сообщение {text} пользователю {user_id}")
    send_to_user(bot, text, None, user_id)

while True:
    try:
        bot.infinity_polling(timeout=10, long_polling_timeout=5)
    except Exception as e:
        logging.error(f"Polling error: {e}")
        time.sleep(5)