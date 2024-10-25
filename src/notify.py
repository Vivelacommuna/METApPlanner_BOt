import schedule
from datetime import datetime
import psycopg2
import time
import telebot
import pytz
import os

bot = telebot.TeleBot(os.getenv('TOKEN'))

conn = psycopg2.connect(
    host=os.getenv('DB_HOST'),
    database=os.getenv('DB_NAME'),
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD'),
)
cur = conn.cursor()

def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(1)

def check_and_send_notifications():
    current_time = datetime.now(pytz.timezone('Europe/Moscow')).time()
    cutoff_time = current_time.replace(hour=current_time.hour + 1)
    current_date = datetime.now(pytz.timezone('Europe/Moscow')).date()
    cur.execute("""
        SELECT employee_id, ru1.username as employee_user, manager_id, ru2.username as manager_user, time
        FROM time_role
            JOIN roles_users ru1 ON ru1.user_id = time_role.employee_id
            JOIN roles_users ru2 ON ru2.user_id = time_role.manager_id
        WHERE time = %s
        AND date = %s;
    """, (cutoff_time.strftime('%H:%M'), current_date.strftime('%Y-%m-%d')))
    conn.commit()
    notifications = cur.fetchall()
    if notifications:
        for notification in notifications:
            employee_id, employee_user, manager_id, manager_user, time = notification
            bot.send_message(employee_id, f"Напоминание: вы записаны на встречу с @{manager_user} на {time}")
            bot.send_message(manager_id, f"Напоминание: @{employee_user} зарегистрирован на встречу c вами на {time}")

schedule.every(10).minutes.do(check_and_send_notifications)