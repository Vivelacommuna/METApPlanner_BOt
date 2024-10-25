from telebot import types

def choice_date(cur, conn, states, call):
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
        SELECT array_agg(DISTINCT date)
        FROM time_role
        WHERE manager_id = COALESCE(%s, manager_id)
        AND employee_id = COALESCE(%s, 0);
    """, (manager_id, employee_id))
    conn.commit()
    dates = cur.fetchone()[0]
    if dates:
        markup = []
        for date in dates:
            date_str = date.strftime('%Y-%m-%d')
            button = types.InlineKeyboardButton(date_str, callback_data=f"date_{date_str}")
            markup.append([button])
        return markup
        
