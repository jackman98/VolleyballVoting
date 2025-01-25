async def safe_edit_message(query, new_text, new_reply_markup=None):
    current_text = query.message.text
    current_reply_markup = query.message.reply_markup

    if current_text == new_text and current_reply_markup == new_reply_markup:
        print("Повідомлення не змінено. Пропускаємо редагування.")
        return

    # Виконуємо редагування
    await query.message.edit_text(new_text, reply_markup=new_reply_markup)
