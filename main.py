from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand, BotCommandScopeAllPrivateChats, BotCommandScopeAllGroupChats
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, \
    filters, Application

from database import init_db, get_queue, add_player, \
    get_all_games, create_game, get_latest_game, get_players_for_game, save_chat, get_all_chats, get_game_by_id, \
    remove_game, move_from_queue, get_confirmed_players_for_game, get_declined_players_for_game
from help import help

import calendar_internal
from utils import safe_edit_message

NUMBER_OF_PLAYERS = int(12)
NEED_TO_NOTIFY = bool(0)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.message.chat if update.message else update.callback_query.message.chat

    if chat.type != "private":
        return

    keyboard = [
        [InlineKeyboardButton("Додати гру", callback_data="start_game_creation")],
        [InlineKeyboardButton("Активні ігри", callback_data="list_games")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.message:
        await update.message.reply_text("Оберіть дію:", reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.message.reply_text("Оберіть дію:", reply_markup=reply_markup)


# Команда для перегляду списку всіх ігор
async def list_games_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    games = get_all_games()
    if not games:
        await query.message.reply_text("Наразі немає доступних ігор.")
        await start(update, context)
        return

    reply_message = "Список всіх ігор:\n\n"
    keyboard = []

    for game in games:
        game_id, date, time, location = game
        reply_message += f"Гра: {game_id}\nДата: {date}\nЧас: {time}\nМісце: {location}\n\n"
        keyboard.append([InlineKeyboardButton(f"Гра {game_id}", callback_data=f"select_game:{game_id}")])

    reply_message += "Виберіть гру:\n\n"

    reply_markup = InlineKeyboardMarkup(keyboard)

    await safe_edit_message(query, reply_message, new_reply_markup=reply_markup)

async def select_game_handler(update, context):
    query = update.callback_query
    await query.answer()

    game_id = query.data.split(":")[1]

    message, _ = game_status(game_id, update)

    keyboard = [
        [InlineKeyboardButton("Скасувати гру", callback_data=f"remove_game:{game_id}")],
        [InlineKeyboardButton("Назад до списку ігор", callback_data="list_games")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await safe_edit_message(query, message, new_reply_markup=reply_markup)


async def start_game_creation_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    # Починаємо процес збору даних
    print("Процес створення гри розпочато.")  # Друк для діагностики
    context.user_data["game_setup"] = {"chat_id": None, "chat_name": None, "date": None, "time": None, "location": None}
    context.user_data["state"] = "awaiting_chat"

    # Завантажуємо чати з бази даних
    chat_list = get_all_chats()

    if not chat_list:
        await query.edit_message_text("Немає доступних чатів для створення гри.")
        return

    # Генеруємо кнопки для вибору чату
    keyboard = [
        [InlineKeyboardButton(chat["name"], callback_data=f"select_chat:{chat["id"]}|{chat["name"]}:")] for chat in chat_list
    ]
    keyboard.append([
        InlineKeyboardButton("Скасувати", callback_data="cancel_game_creation")
    ])

    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text("Оберіть чат для гри:", reply_markup=reply_markup)

async def select_chat_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    state = context.user_data.get("state")
    game_data = context.user_data.get("game_setup", None)

    if not game_data:
        return

    print(f"Поточні дані: {game_data}")  # Друк у консоль для перевірки

    if state == "awaiting_chat" and query.data.startswith("select_chat"):
        data = query.data.split(":")[1]
        chat_id, chat_name = data.split("|")
        game_data["chat_id"] = int(chat_id)
        game_data["chat_name"] = chat_name
        context.user_data["state"] = "awaiting_date"
        calendar_markup = calendar_internal.create_calendar()
        await query.edit_message_text("Введіть дату гри (наприклад, 2025-01-20):", reply_markup=calendar_markup)


# Обробка текстового вводу для збору даних
async def handle_game_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = context.user_data.get("state")
    game_data = context.user_data.get("game_setup", None)

    if not game_data:
        return

    print(f"Поточні дані: {game_data}")  # Друк у консоль для перевірки

    if game_data["location"] is None:
        game_data["location"] = update.message.text
        print(f"Збережено місце: {game_data['location']}")

        # Усі дані зібрані, показуємо їх користувачеві
        message = (
            f"Гра готова до збереження:\n"
            f"📅 Дата: {game_data['date']}\n"
            f"⏰ Час: {game_data['time']}\n"
            f"📍 Місце: {game_data['location']}\n\n"
        )

        # Кнопки для голосування
        keyboard = [
            [
                InlineKeyboardButton("Зберегти", callback_data="save_game"),
                InlineKeyboardButton("Скасувати", callback_data="cancel_game_creation")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(message, reply_markup=reply_markup)

# Команда /save_game
async def save_game_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    game_data = context.user_data.get("game_setup", None)

    if not game_data or None in game_data.values():
        await update.message.reply_text("Недостатньо даних для збереження. Виконайте команду /add_game спочатку.")
        return

    print(f"Поточні дані: {game_data}")  # Друк у консоль для перевірки

    # Додаємо гру до бази даних
    create_game(game_data["chat_id"], game_data["date"], game_data["time"], game_data["location"])
    game = get_latest_game()

    # Скидаємо дані
    context.user_data["game_setup"] = None

    for index, value in enumerate(game):
        print(f"Елемент {index}: {value}")

    message, reply_markup = game_status(game[0], update)

    await query.edit_message_text(message)

    sent_message = await context.bot.send_message(
        chat_id=game[1],
        text=message,
        reply_markup=reply_markup
    )
    try:
        # Перевіряємо прикріплення повідомлення
        await context.bot.pin_chat_message(chat_id=game[1], message_id=sent_message.message_id)
    except Exception as e:
        print(f"Не вдалося прикріпити повідомлення: {e}")

async def remove_game_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    game_id = query.data.split(":")[1]

    remove_game(game_id)

    await query.message.reply_text("Гру успішно скасовано!")
    await list_games_handler(update, context)

async def cancel_game_creation_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if "game_setup" in context.user_data:
        context.user_data["game_setup"] = None
        await query.edit_message_text("Налаштування гри скасовано.")
    else:
        await query.edit_message_text("Немає активного налаштування гри для скасування.")

    await start(update, context)

async def vote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    name = query.from_user.first_name
    user_id = query.from_user.id

    game_id = query.data.split(":")[1]

    confirmed_players = get_confirmed_players_for_game(game_id)

    player = next((player for player in confirmed_players if player[0] == user_id), None)

    if player:
        if NEED_TO_NOTIFY:
            await query.message.reply_text("Ви вже записані на гру.")
    elif len(confirmed_players) < NUMBER_OF_PLAYERS:
        add_player(user_id, name, game_id, "confirmed")
        if NEED_TO_NOTIFY:
            await query.message.reply_text(f"{name}, ви додані до списку учасників!")
    elif user_id not in get_queue(game_id):
        add_player(user_id, name, game_id, "confirmed")
        if NEED_TO_NOTIFY:
            await query.message.reply_text(f"{name}, список учасників повний. Ви додані до черги.")
    else:
        if NEED_TO_NOTIFY:
            await query.message.reply_text("Ви вже у черзі.")

# Відміна участі
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    name = query.from_user.first_name
    user_id = query.from_user.id

    game_id = query.data.split(":")[1]

    players = get_players_for_game(game_id)

    player = next((player for player in players if player[0] == user_id), None)

    if player and player[2] == "confirmed":
        add_player(user_id, name, game_id, "declined")
        if NEED_TO_NOTIFY:
            await query.message.reply_text(f"{name}, ви скасували участь у грі.")

        next_in_queue = move_from_queue(game_id)
        if next_in_queue:
            if NEED_TO_NOTIFY:
                await query.message.reply_text(f"{next_in_queue} переміщено з черги до списку учасників.")
    elif user_id in get_queue(game_id):
        add_player(user_id, name, game_id, "declined")
        if NEED_TO_NOTIFY:
            await query.message.reply_text(f"{name}, ви видалені з черги.")
    else:
        if NEED_TO_NOTIFY:
            await query.message.reply_text(f"{name}, немає, що скасовувати :)")

async def vote_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    game_id = query.data.split(":")[1]
    game = get_game_by_id(game_id)

    if not game:
        await query.message.reply_text("Ця гра не активна.")

        return

    if query.data.startswith("vote_yes"):
        await vote(update, context)
    elif query.data.startswith("vote_no"):
        await cancel(update, context)

    message, reply_markup = game_status(game_id, update)
    await safe_edit_message(query, message, new_reply_markup = reply_markup)

def game_status(game_id, update: Update):
    game = get_game_by_id(game_id)
    if not game:
        return

    max_players = NUMBER_OF_PLAYERS

    confirmed = [player[1] for player in get_confirmed_players_for_game(game_id)]
    declined = [player[1] for player in get_declined_players_for_game(game_id)]

    # Формуємо чергу
    queue = confirmed[max_players:]  # Усі, хто перевищує ліміт
    confirmed = confirmed[:max_players]

    message = (
            f"📅 Дата: {game[1]}\n"
            f"⏰ Час: {game[2]}\n"
            f"📍 Місце: {game[3]}\n\n"
            f"✅ Учасники ({len(confirmed)} / {max_players}):\n" +
            ("\n".join(f"- {name}" for name in confirmed) if confirmed else "Немає записаних") +
            "\n\n"
            f"❌ Відмовились ({len(declined)}):\n" +
            ("\n".join(f"- {name}" for name in declined) if declined else "Ніхто не відмовився") +
            "\n\n"
            f"📋 Черга ({len(queue)}):\n" +
            ("\n".join(f"- {name}" for name in queue) if queue else "Черга порожня")
    )

    confirm_button = InlineKeyboardButton("Я буду", callback_data=f"vote_yes:{game_id}")
    decline_button = InlineKeyboardButton("Я не буду", callback_data=f"vote_no:{game_id}")

    keyboard = [
        [confirm_button],
        [decline_button]
        ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    return message, reply_markup

async def game_status_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    game_id = query.data.split(":")[1]

    message, _ = game_status(game_id, update)

    keyboard = [
        [InlineKeyboardButton("Назад до списку ігор", callback_data="list_games")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(message, reply_markup=reply_markup)

async def track_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.message.chat
    save_chat(chat.id, chat.title)
    print(f"Чат збережено: ID={chat.id}, Назва={chat.title}")

async def set_bot_commands(application):
    chat_commands = [
        BotCommand("track_chat", "Слідкувати за чатом")
    ]

    private_commands = [
        BotCommand("start", "Розпочати")
    ]

    await application.bot.set_my_commands(chat_commands, scope=BotCommandScopeAllGroupChats())
    await application.bot.set_my_commands(private_commands, scope=BotCommandScopeAllPrivateChats())

if __name__ == "__main__":
    init_db()

    async def post_init(application: Application) -> None:
        await set_bot_commands(application)

    app = ApplicationBuilder().token("TOKEN").post_init(post_init).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help))
    app.add_handler(CommandHandler("track_chat", track_chat))

    app.add_handler(CallbackQueryHandler(start_game_creation_handler, pattern="^start_game_creation$"))
    app.add_handler(CallbackQueryHandler(cancel_game_creation_handler, pattern="^cancel_game_creation$"))
    app.add_handler(CallbackQueryHandler(save_game_handler, pattern="^save_game$"))
    app.add_handler(CallbackQueryHandler(remove_game_handler, pattern="^remove_game:"))
    app.add_handler(CallbackQueryHandler(game_status_handler, pattern="^game_status:"))
    app.add_handler(CallbackQueryHandler(list_games_handler, pattern="^list_games$"))
    app.add_handler(CallbackQueryHandler(select_game_handler, pattern="^select_game:"))
    app.add_handler(CallbackQueryHandler(select_chat_handler, pattern="^select_chat:"))
    app.add_handler(CallbackQueryHandler(calendar_internal.date_selection_handler, pattern="^(day:|prev_month:|next_month:|ignore)"))
    app.add_handler(CallbackQueryHandler(calendar_internal.time_selection_handler, pattern="^(hour:|minute:|change_hour)"))
    app.add_handler(CallbackQueryHandler(vote_handler, pattern="^vote_yes:"))
    app.add_handler(CallbackQueryHandler(vote_handler, pattern="^vote_no:"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_game_input))

    print("Бот запущено...")
    app.run_polling()
