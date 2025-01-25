from telegram import Update
from telegram.ext import ContextTypes

async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    commands = """
Список доступних команд:
/set_game - Налаштувати гру (дата, час, місце)
/list_games - Переглянути список всіх ігор
/game_status - Переглянути статус поточної гри
/vote - Проголосувати за участь у грі
/cancel - Скасувати участь у грі
/help - Показати список команд

Інструкція:
1. Використовуйте /set_game, щоб встановити або змінити параметри гри.
2. Збережіть гру після введення всіх параметрів.
3. Переглядайте всі створені ігри через /list_games.
4. Проголосуйте за участь у грі за допомогою /vote.
5. Скасуйте своє бронювання через /cancel.

Якщо у вас виникли питання, звертайтесь до адміністратора групи.
    """
    await update.message.reply_text(commands)