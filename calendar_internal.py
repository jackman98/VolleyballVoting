from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import calendar
from datetime import datetime

def create_calendar(year=None, month=None):
    """
    Генерує кнопкову розмітку календаря.
    :param year: Рік для відображення.
    :param month: Місяць для відображення.
    :return: InlineKeyboardMarkup з кнопками.
    """
    now = datetime.now()
    year = year or now.year
    month = month or now.month

    keyboard = [[
        InlineKeyboardButton(f"{calendar.month_name[month]} {year}", callback_data="ignore")
    ], [
        InlineKeyboardButton(day, callback_data="ignore") for day in ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Нд"]
    ]]

    # Заголовок з поточним місяцем і роком

    # Дні тижня

    # Дні місяця
    month_days = calendar.monthcalendar(year, month)
    for week in month_days:
        row = []
        for day in week:
            if day == 0:  # Порожнє місце в календарі
                row.append(InlineKeyboardButton(" ", callback_data="ignore"))
            else:
                row.append(InlineKeyboardButton(str(day), callback_data=f"day:{year}-{month:02}-{day:02}"))
        keyboard.append(row)

    # Кнопки для перемикання місяців
    keyboard.append([
        InlineKeyboardButton("⬅️", callback_data=f"prev_month:{year}-{month}"),
        InlineKeyboardButton("➡️", callback_data=f"next_month:{year}-{month}")
    ])
    keyboard.append([
        InlineKeyboardButton("Скасувати", callback_data="cancel_game_creation")
    ])

    return InlineKeyboardMarkup(keyboard)

async def date_selection_handler(update, context):
    """
    Обробляє вибір дати через календар.
    """
    query = update.callback_query
    await query.answer()

    data = query.data

    if data.startswith("day:"):
        # Обробка вибору дати
        selected_date = data.split(":")[1]
        game_data = context.user_data.get("game_setup", None)

        if not game_data:
            return

        print(f"Поточні дані: {game_data}")  # Друк у консоль для перевірки

        # Автоматичний перехід між полями
        if game_data["date"] is None:
            game_data["date"] = selected_date
            print(f"Збережено дату: {game_data['date']}")

            await query.message.edit_text("Введіть час гри (наприклад, 18:30):", reply_markup=create_time_picker())
    elif data.startswith("prev_month:"):
        # Перехід до попереднього місяця
        year, month = map(int, data.split(":")[1].split("-"))
        if month == 1:
            year -= 1
            month = 12
        else:
            month -= 1
        await query.message.edit_reply_markup(reply_markup=create_calendar(year, month))
    elif data.startswith("next_month:"):
        # Перехід до наступного місяця
        year, month = map(int, data.split(":")[1].split("-"))
        if month == 12:
            year += 1
            month = 1
        else:
            month += 1
        await query.message.edit_reply_markup(reply_markup=create_calendar(year, month))
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def create_time_picker(selected_hour=None):
    keyboard = []

    if selected_hour is None:
        # Вибір години (0-23)
        row = []
        for hour in range(24):
            row.append(InlineKeyboardButton(f"{hour:02}", callback_data=f"hour:{hour}"))
            if len(row) == 6:  # Робимо по 6 кнопок у рядку
                keyboard.append(row)
                row = []
        if row:  # Додаємо залишок кнопок
            keyboard.append(row)
    else:
        # Вибір хвилин (0-59)
        row = []
        for minute in range(0, 60, 5):  # Інтервал вибору хвилин — кожні 5 хвилин
            row.append(InlineKeyboardButton(f"{minute:02}", callback_data=f"minute:{selected_hour}:{minute}"))
            if len(row) == 6:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        # Кнопка для повернення до вибору години
        keyboard.append([InlineKeyboardButton("⬅️ Змінити годину", callback_data="change_hour")])
        keyboard.append([
            InlineKeyboardButton("Скасувати", callback_data="cancel_game_creation")
        ])
    return InlineKeyboardMarkup(keyboard)
async def time_selection_handler(update, context):
    """
    Обробляє вибір години та хвилин через кнопки.
    """
    query = update.callback_query
    await query.answer()

    data = query.data

    state = context.user_data.get("state")
    game_data = context.user_data.get("game_setup", None)

    if not game_data:
        return

    print(f"Поточні дані: {game_data}")  # Друк у консоль для перевірки

    if data.startswith("hour:"):
        # Користувач обрав годину
        selected_hour = int(data.split(":")[1])
        reply_markup = create_time_picker(selected_hour)
        await query.message.edit_text(
            f"Ви обрали годину: {selected_hour:02}\nОберіть хвилини:",
            reply_markup=reply_markup
        )
    elif data.startswith("minute:"):
        # Користувач обрав хвилину
        _, hour, minute = data.split(":")

        if game_data["time"] is None:
            game_data["time"] = f"{int(hour):02}:{int(minute):02}"
            print(f"Збережено час: {game_data['time']}")
            await query.message.edit_text("Введіть місце проведення гри:")
    elif data == "change_hour":
        # Користувач повертається до вибору години
        reply_markup = create_time_picker()
        await query.message.edit_text("Оберіть годину:", reply_markup=reply_markup)
