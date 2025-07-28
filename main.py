from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, ConversationHandler, filters
)

import os

# === Настройки ===
TOKEN = os.getenv("BOT_TOKEN")

CHATS = {
    "Test2": -1002501155082,
    "Test1": -1002499900889
}

TOPICS = {
    "Новости": {
        -1002501155082: 11,
        -1002499900889: 2
    },
    "Оплаты": {
        -1002501155082: 8,
        -1002499900889: 7
    },
    "Мероприятия": {
        -1002501155082: 6,
        -1002499900889: 4
    }
}

SELECT_CHATS, SELECT_TOPIC, ENTER_MESSAGE, ENTER_PHOTO = range(4)

def build_chat_buttons(selected=None):
    buttons = []
    for name in CHATS:
        checked = "✅ " if selected and name in selected else ""
        buttons.append([InlineKeyboardButton(f"{checked}{name}", callback_data=name)])
    buttons.append([InlineKeyboardButton("➡ Далее", callback_data="next")])
    return buttons

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["selected_chats"] = set()
    await update.message.reply_text(
        "Выбери чаты для рассылки:",
        reply_markup=InlineKeyboardMarkup(build_chat_buttons())
    )
    return SELECT_CHATS

async def select_chats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "next":
        selected = context.user_data["selected_chats"]
        if not selected:
            await query.edit_message_text("❗ Сначала выбери хотя бы один чат.")
            return SELECT_CHATS

        selected_ids = {CHATS[name] for name in selected}
        available_topics = [
            name for name, ids in TOPICS.items()
            if selected_ids.issubset(set(ids.keys()))
        ]
        if not available_topics:
            await query.edit_message_text("❗ Нет общей темы во всех выбранных чатах.")
            return ConversationHandler.END

        buttons = [[InlineKeyboardButton(t, callback_data=t)] for t in available_topics]
        await query.edit_message_text("Выбери тему:", reply_markup=InlineKeyboardMarkup(buttons))
        return SELECT_TOPIC

    chats = context.user_data["selected_chats"]
    if data in chats:
        chats.remove(data)
    else:
        chats.add(data)
    await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(build_chat_buttons(chats)))
    return SELECT_CHATS

async def select_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["topic"] = query.data
    await query.edit_message_text(f"Тема выбрана: {query.data}\nТеперь введи текст сообщения:")
    return ENTER_MESSAGE

async def enter_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["text"] = update.message.text
    await update.message.reply_text("Хочешь прикрепить фото? Отправь его сейчас или напиши 'нет'")
    return ENTER_PHOTO

async def enter_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chats = context.user_data["selected_chats"]
    topic = context.user_data["topic"]
    text = context.user_data["text"]
    selected_ids = [CHATS[name] for name in chats]

    for chat_id in selected_ids:
        thread_id = TOPICS[topic][chat_id]
        try:
            if update.message.photo:
                photo = update.message.photo[-1].file_id
                await context.bot.send_photo(
                    chat_id=chat_id,
                    message_thread_id=thread_id,
                    photo=photo,
                    caption=text
                )
            elif update.message.text.lower() == "нет":
                await context.bot.send_message(
                    chat_id=chat_id,
                    message_thread_id=thread_id,
                    text=text
                )
        except Exception as e:
            await update.message.reply_text(f"Ошибка при отправке в чат {chat_id}: {e}")

    await update.message.reply_text("✅ Сообщение разослано.")
    return ConversationHandler.END

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            SELECT_CHATS: [CallbackQueryHandler(select_chats)],
            SELECT_TOPIC: [CallbackQueryHandler(select_topic)],
            ENTER_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_message)],
            ENTER_PHOTO: [MessageHandler(filters.PHOTO | filters.TEXT, enter_photo)],
        },
        fallbacks=[]
    )

    app.add_handler(conv)
    app.run_polling()

if __name__ == "__main__":
    main()