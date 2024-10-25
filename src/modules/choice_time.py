from telebot import types

def choice_time(cur, conn, states,call):
    manager_id = None
    employee_id = None
    if not states[call.from_user.id]['is_manager'] and not states[call.from_user.id]['is_del']:
        if states[call.from_user.id]['manager_id']:
            manager_id = states[call.from_user.id]['manager_id']
    if states[call.from_user.id]['is_manager']:
        manager_id = call.from_user.id
    if not states[call.from_user.id]['is_manager']:
        employee_id = call.from_user.id
    if not states[call.from_user.id]['is_del']:
        employee_id = None
    cur.execute("""
        SELECT array_agg(DISTINCT time)
        FROM time_role
        WHERE manager_id = COALESCE(%s, manager_id)
        AND employee_id = COALESCE(%s, 0)
        AND date = %s;
    """, (manager_id, employee_id, states[call.from_user.id]['date']))
    conn.commit()
    times_array = cur.fetchone()[0]
    if times_array:
        markup = []
        for time in times_array:
            formatted_time = time.strftime('%H:%M')
            markup.append([types.InlineKeyboardButton(formatted_time, callback_data=f"time_{formatted_time}")])
        return markup