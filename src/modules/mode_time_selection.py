from main import send_to_user
import logging

logging.basicConfig(level=logging.INFO)

def del_manager_time(cur, conn, call, states, time):
    cur.execute("""
        DELETE FROM time_role
        WHERE manager_id = %s
        AND time = %s
        AND date = %s
    """, (call.from_user.id, time, states[call.from_user.id]['date']))
    conn.commit()

def del_employee_time(cur, conn, call, states, time):
    manager_id = None
    try:
        with conn:
            cur.execute("""
                BEGIN;
                UPDATE time_role
                SET employee_id = 0
                WHERE employee_id = %s
                AND time = %s
                AND date = %s
                RETURNING manager_id;
            """, (call.from_user.id, time, states[call.from_user.id]['date']))
            conn.commit()
            result = cur.fetchone()
            if result:
                manager_id = result[0]
            else:
                logging.warning(f"Не удалось удалить время {call.from_user.id}, {time}, {states[call.from_user.id]['date']}")
    except Exception as e:
        logging.error(f"Не удалось удалить время {call.from_user.id}, {time}, {states[call.from_user.id]['date']}, {e}")
    return manager_id

def set_employee_time(cur, conn, call, states, time):
    manager_id = None
    try:
        with conn:
            cur.execute("""
                BEGIN;
                UPDATE time_role
                SET employee_id = %s
                WHERE time = %s
                AND date = %s
                RETURNING manager_id;
                """, (call.from_user.id, time, states[call.from_user.id]['date']))
            conn.commit()
            result = cur.fetchone()
            if result:
                manager_id = result[0]
            else:
                logging.warning(f"Не удалось добавить время {call.from_user.id}, {time}, {states[call.from_user.id]['date']}")
    except Exception as e:
        logging.error(f"Не удалось добавить время {call.from_user.id}, {time}, {states[call.from_user.id]['date']}, {e}")
    return manager_id

def mode_time_selection(bot, cur, conn, states, call, time):
    if states[call.from_user.id]['is_manager'] and states[call.from_user.id]['is_del']:
        del_manager_time(cur, conn, call, states, time)
        logging.info(f"{call.from_user.id}, {time}, del_manager_time")
        bot.send_message(call.from_user.id, "Время удалено")
    elif not states[call.from_user.id]['is_manager'] and states[call.from_user.id]['is_del']:
        manager_id = del_employee_time(cur, conn, call, states, time)
        if manager_id:
            send_to_user(bot, f"снялся со встречи на {time}", call.from_user, manager_id)
            bot.send_message(call.from_user.id, f"Вы удалили время на {time}")
        else:
            bot.send_message(call.from_user.id, "Не удалось удалить время, попробуйте ещё раз")
        logging.info(f"{manager_id}, {call.from_user.id}, {time}, del_employee_time")
    else:
        manager_id = set_employee_time(cur, conn, call, states, time)
        if manager_id:
            send_to_user(bot, f"записался к вам на встречу на {time}", call.from_user, manager_id)
            bot.send_message(call.from_user.id, f"Вы записаны на встречу с руководителем на {time}")
        else:
            bot.send_message(call.from_user.id, "К сожалению время было удалено")
        logging.info(f"{manager_id}, {call.from_user.id}, {time}, set_employee_time")