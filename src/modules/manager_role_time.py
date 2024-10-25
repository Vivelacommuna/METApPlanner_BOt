import telebot
from telebot import types
import psycopg2
import datetime
import pytz
import os
import logging

logging.basicConfig(level=logging.INFO)

bot = telebot.TeleBot(os.getenv('TOKEN'))

conn = psycopg2.connect(
    host=os.getenv('DB_HOST'),
    database=os.getenv('DB_NAME'),
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD'),
)
cur = conn.cursor()

time = {}

def get_dates_ahead(days_ahead=7):
    today = datetime.datetime.now(pytz.timezone('Europe/Moscow'))
    dates = []
    markup = []
    for i in range(days_ahead):
        date = today + datetime.timedelta(days=i)
        dates.append(date.strftime('%Y-%m-%d'))
        button = types.InlineKeyboardButton(date.strftime('%Y-%m-%d'), callback_data=f"hours_manager_role_time_{date.strftime('%Y-%m-%d')}")
        markup.append([button])
    return markup

def get_hours_ahead(date=None, times_ahead=24):
    now = datetime.datetime.now(pytz.timezone('Europe/Moscow'))
    current_day = now.date()
    chosen_day = datetime.datetime.strptime(date, '%Y-%m-%d').date()
    if chosen_day > current_day:
        start_hour = 0
    else:
        start_hour = now.hour
    markup = types.InlineKeyboardMarkup()
    row = []
    for i in range(start_hour, times_ahead):
        time = datetime.datetime.combine(now.date(), datetime.datetime.min.time()) + datetime.timedelta(hours=i)
        button = types.InlineKeyboardButton(time.strftime('%H:%M'), callback_data=f"minutes_manager_role_time_{time.strftime('%H:%M')}")
        row.append(button)
        if len(row) == 4 or i == times_ahead - 1:
            markup.row(*row)
            row = []
    return markup

def get_minutes_ahead(hour=None):
    now = datetime.datetime.now(pytz.timezone('Europe/Moscow'))
    current_minute = now.minute
    chosen_hour = datetime.datetime.strptime(hour, '%H:%M').time().hour
    minute_options = [0, 15, 30, 45]
    avalable_minutes = []
    for i in range(len(minute_options)):
        if chosen_hour == now.hour:
            if minute_options[i] >= current_minute:
                avalable_minutes.append(minute_options[i])
        else:
            avalable_minutes.append(minute_options[i])
    if not avalable_minutes:
        return None
    markup = types.InlineKeyboardMarkup()
    row = []
    for i in avalable_minutes:
        time = datetime.datetime.combine(now.date(), datetime.datetime.min.time()) + datetime.timedelta(hours=chosen_hour, minutes=i)
        button = types.InlineKeyboardButton(time.strftime('%H:%M'), callback_data=f"choice_manager_role_time_{time.strftime('%H:%M')}")
        row.append(button)
        if len(row) == 2 or i == 45:
            markup.row(*row)
            row = []
    return markup

def choice_manager_role_time(call):
    callback_data = call.data
    time[call.from_user.id]['time'] = callback_data.split('_')[-1]
    bot.answer_callback_query(call.id)
    bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.id)
    markup = types.InlineKeyboardMarkup(row_width=2)
    item1 = types.InlineKeyboardButton("Выбрать другой день", callback_data='add_manager_role_time')
    item2 = types.InlineKeyboardButton("Выбрать другое время на этот день", callback_data="hours_manager_role_time")
    item2 = types.InlineKeyboardButton("Назад", callback_data="manager_role_time")
    markup.add(item1)
    markup.add(item2)
    set_manager_time(bot, cur, conn, call)
    bot.send_message(call.from_user.id, "Хотите добавить другое время?", reply_markup=markup)

def manager_role_time(call):
    if call.from_user.id not in time:
        time[call.from_user.id] = {}
    bot.answer_callback_query(call.id)
    bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.id)
    markup = types.InlineKeyboardMarkup()
    item1 = types.InlineKeyboardButton("Хочу добавить время", callback_data='add_manager_role_time')
    item2 = types.InlineKeyboardButton("Хочу удалить время", callback_data='del_time')
    markup.add(item1, item2)
    bot.send_message(call.from_user.id, "Что вы хотите сделать?", reply_markup=markup)

def add_manager_role_time(call):
    bot.answer_callback_query(call.id)
    bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.id)
    markup = get_dates_ahead()
    markup.append([types.InlineKeyboardButton("Назад", callback_data="manager_role_time")])
    bot.send_message(call.from_user.id, "Выберите время для проведения встречи:", reply_markup=types.InlineKeyboardMarkup(markup))

def hours_manager_role_time(call):
    callback_data = call.data
    time[call.from_user.id]['date'] = callback_data.split('_')[-1]
    bot.answer_callback_query(call.id)
    markup = get_hours_ahead(time[call.from_user.id]['date'])
    back_button = types.InlineKeyboardButton("Назад", callback_data="add_manager_role_time")
    markup.add(back_button)
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=markup)

def minutes_manager_role_time(call):
    callback_data = call.data
    time[call.from_user.id]['hour'] = callback_data.split('_')[-1]
    bot.answer_callback_query(call.id)
    markup = get_minutes_ahead(time[call.from_user.id]['hour'])
    if not markup:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Назад", callback_data="add_manager_role_time"))
        bot.send_message(call.from_user.id, "Выберите, пожалуйста, другое время", reply_markup=markup)
    types.InlineKeyboardButton("Назад", callback_data="add_manager_role_time")
    markup.add(types.InlineKeyboardButton("Назад", callback_data="add_manager_role_time"))
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=markup)

def set_manager_time(bot, cur, conn, call):
    cur.execute("""
        INSERT INTO time_role (time, employee_id, manager_id, date)
        VALUES (%s, 0, %s, %s)
        ON CONFLICT (time, manager_id, date) DO NOTHING
        RETURNING *;
    """, (time[call.from_user.id]['time'], call.from_user.id, 
    time[call.from_user.id]['date']))
    conn.commit()
    result = cur.fetchone()
    if result:
        bot.send_message(call.from_user.id, "Время добавлено")
        logging.info(f"{result}, {call.from_user.id}, {time[call.from_user.id]['date']}, {time[call.from_user.id]['time']}, set_manager_time")
    else:
        logging.info(f"{call.from_user.id}, {time[call.from_user.id]['date']}, {time[call.from_user.id]['time']}, set_manager_time")
        bot.send_message(call.from_user.id, "Время уже занято")

# регистрируем хендлеры для модуля manager_role_time
def register_manager_role_time_handlers(bot):
    bot.register_callback_query_handler(manager_role_time, lambda call: call.data == 'manager_role_time')
    bot.register_callback_query_handler(add_manager_role_time, lambda call: call.data == 'add_manager_role_time')
    bot.register_callback_query_handler(hours_manager_role_time, lambda call: call.data.startswith('hours_manager_role_time'))
    bot.register_callback_query_handler(minutes_manager_role_time, lambda call: call.data.startswith('minutes_manager_role_time'))
    bot.register_callback_query_handler(choice_manager_role_time, lambda call: call.data.startswith('choice_manager_role_time'))