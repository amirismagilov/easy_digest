import os
import sys
import django
import logging

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    filters
)
from asgiref.sync import sync_to_async

# --- Django setup ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

# --- Импорт моделей ---
from admin_panel.models import User, DigestGroup, Channel

# --- Логирование ---
logging.basicConfig(level=logging.INFO)

# --- Состояния для ConversationHandler ---
ASK_GROUP_NAME = 1
SELECT_GROUP_FOR_CHANNEL = 2
ENTER_CHANNEL_USERNAME = 3

# --- Создание или обновление пользователя ---
@sync_to_async
def get_or_create_user(tg_id, username):
    user, created = User.objects.get_or_create(
        telegram_id=tg_id,
        defaults={'username': username}
    )
    if not created and username and user.username != username:
        user.username = username
        user.save()
    return user

# --- Получение групп пользователя ---
@sync_to_async
def get_user_groups(tg_id):
    user = User.objects.filter(telegram_id=tg_id).first()
    if not user:
        return []
    return list(user.digestgroup_set.values_list("name", flat=True))

# --- Сохранение новой группы ---
@sync_to_async
def create_group(tg_id, name):
    user = User.objects.get(telegram_id=tg_id)
    DigestGroup.objects.create(user=user, name=name)

# --- Сохранение канала и привязка к группе ---
@sync_to_async
def save_channel_to_group(tg_id, group_name, username):
    user = User.objects.get(telegram_id=tg_id)
    group = DigestGroup.objects.get(user=user, name=group_name)
    channel, _ = Channel.objects.get_or_create(username=username, defaults={"title": username})
    group.channels.add(channel)

# --- /start команда с меню ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    username = update.effective_user.username
    await get_or_create_user(tg_id, username)

    keyboard = [
        [InlineKeyboardButton("➕ Добавить группу", callback_data="add_group")],
        [InlineKeyboardButton("📋 Мои группы", callback_data="show_groups")],
        [InlineKeyboardButton("📡 Добавить канал", callback_data="add_channel")],
        [InlineKeyboardButton("📤 Запросить дайджест", callback_data="get_digest")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "Привет! Я готов собрать тебе дайджест по каналам. Напиши /help, чтобы узнать больше.",
        reply_markup=reply_markup
    )

# --- Обработка inline-кнопок из главного меню ---
async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    tg_id = query.from_user.id

    if query.data == "add_group":
        await query.message.reply_text("Как назвать новую группу каналов?")
        return ASK_GROUP_NAME

    elif query.data == "show_groups":
        groups = await get_user_groups(tg_id)
        if not groups:
            await query.message.reply_text("У тебя пока нет ни одной группы.")
        else:
            # Кнопки "Показать каналы"
            buttons = [
                [InlineKeyboardButton(f"📂 {g}", callback_data=f"list_channels::{g}")]
                for g in groups
            ]
            reply_markup = InlineKeyboardMarkup(buttons)
            await query.message.reply_text("Твои группы:", reply_markup=reply_markup)
        return ConversationHandler.END

    elif query.data == "add_channel":
        groups = await get_user_groups(tg_id)
        if not groups:
            await query.message.reply_text("У тебя нет групп. Сначала создай хотя бы одну.")
            return ConversationHandler.END

        context.user_data["group_list"] = groups
        buttons = [[InlineKeyboardButton(g, callback_data=f"group_{i}")] for i, g in enumerate(groups)]
        reply_markup = InlineKeyboardMarkup(buttons)

        await query.message.reply_text("Выбери группу, в которую добавить канал:", reply_markup=reply_markup)
        return SELECT_GROUP_FOR_CHANNEL

    elif query.data == "get_digest":
        await query.message.reply_text("⚙️ Генерация дайджеста пока в разработке 😊")

    elif query.data.startswith("list_channels::"):
        group_name = query.data.split("::")[1]
        channels = await get_group_channels(tg_id, group_name)

        if not channels:
            await query.message.reply_text(f"В группе «{group_name}» пока нет каналов.")
            return ConversationHandler.END

        # Формируем сообщение и кнопки
        message_lines = [f"Каналы в «{group_name}»:"]

        buttons = []

        for username in channels:
            message_lines.append(f"@{username}")
            buttons.append([
                InlineKeyboardButton(
                    text=f"🗑 Удалить @{username}",
                    callback_data=f"remove_channel::{group_name}::{username}"
                )
            ])

        # Добавляем кнопку "добавить ещё"
        buttons.append([
            InlineKeyboardButton(
                text="➕ Добавить канал",
                callback_data="add_channel"
            )
        ])

        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.reply_text("\n".join(message_lines), reply_markup=reply_markup)
        return ConversationHandler.END
    
    elif query.data.startswith("remove_channel::"):
        _, group_name, username = query.data.split("::")

        success = await remove_channel_from_group(tg_id, group_name, username)
        if success:
            await query.message.reply_text(f"🗑 Канал @{username} удалён из группы «{group_name}»")
        else:
            await query.message.reply_text("❌ Не удалось удалить канал.")
        return ConversationHandler.END

    return ConversationHandler.END

# --- Сохранение новой группы ---
async def handle_group_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    group_name = update.message.text.strip()

    await create_group(tg_id, group_name)
    await update.message.reply_text(f"✅ Группа «{group_name}» успешно создана!")
    return ConversationHandler.END

# --- Выбор группы для добавления канала ---
async def select_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    selected = query.data
    if selected.startswith("group_"):
        index = int(selected.replace("group_", ""))
        group_name = context.user_data["group_list"][index]
        context.user_data["selected_group"] = group_name

        await query.message.reply_text("Теперь отправь username канала (например: @bbbreaking)")
        return ENTER_CHANNEL_USERNAME

# --- Добавление username канала в группу ---
async def enter_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    group = context.user_data["selected_group"]
    username = update.message.text.strip().lstrip("@")

    await save_channel_to_group(tg_id, group, username)
    await update.message.reply_text(
        f"✅ Канал @{username} добавлен в группу «{group}».\n\n"
        "Что дальше?",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📡 Добавить ещё канал", callback_data="add_channel")],
            [InlineKeyboardButton("📤 Запросить дайджест", callback_data="get_digest")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")],
        ])
    )
    return ConversationHandler.END

# --- Получение каналов из группы---
@sync_to_async
def get_group_channels(tg_id, group_name):
    user = User.objects.filter(telegram_id=tg_id).first()
    if not user:
        return []
    group = DigestGroup.objects.filter(user=user, name=group_name).first()
    if not group:
        return []
    return list(group.channels.values_list("username", flat=True))

# --- Удаление канала---
@sync_to_async
def remove_channel_from_group(tg_id, group_name, username):
    user = User.objects.filter(telegram_id=tg_id).first()
    if not user:
        return False
    group = DigestGroup.objects.filter(user=user, name=group_name).first()
    if not group:
        return False
    channel = Channel.objects.filter(username=username).first()
    if channel:
        group.channels.remove(channel)
        return True
    return False

# --- Запуск Telegram-бота ---
def run_bot():
    app = ApplicationBuilder().token("7800377470:AAEcDECVkGVzOdXrqJRO3lZxo9XMQkdE8Uc").build()

    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(handle_button)],
        states={
            ASK_GROUP_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_group_name)],
            SELECT_GROUP_FOR_CHANNEL: [CallbackQueryHandler(select_group)],
            ENTER_CHANNEL_USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_channel)],
        },
        fallbacks=[],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)
    app.run_polling()

if __name__ == "__main__":
    run_bot()