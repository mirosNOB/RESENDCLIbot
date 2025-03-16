#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import sqlite3
import asyncio
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Токен вашего бота
TOKEN = "8067130497:AAG4Xs4Djfymg082Ezj6bXQ1E5C6ckzW8Ps"

# Создаем или открываем базу данных
def setup_database():
    conn = sqlite3.connect('feedback.db', check_same_thread=False)
    cursor = conn.cursor()
    
    # Проверяем, существует ли таблица feedback
    cursor.execute("PRAGMA table_info(feedback)")
    columns = cursor.fetchall()
    column_names = [column[1] for column in columns]
    
    # Создаем таблицу для хранения обращений, если она не существует
    if not columns:
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            message TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_replied INTEGER DEFAULT 0,
            feedback_type TEXT
        )
        ''')
    else:
        # Проверяем, есть ли столбец feedback_type
        if 'feedback_type' not in column_names:
            logger.info("Добавление столбца feedback_type в таблицу feedback")
            cursor.execute("ALTER TABLE feedback ADD COLUMN feedback_type TEXT")
    
    # Создаем таблицу для хранения администраторов
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS admins (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        added_by INTEGER,
        added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Создаем таблицу для хранения ответов на сообщения
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS replies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        feedback_id INTEGER,
        admin_id INTEGER,
        reply_text TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (feedback_id) REFERENCES feedback (id),
        FOREIGN KEY (admin_id) REFERENCES admins (user_id)
    )
    ''')
    
    conn.commit()
    return conn, cursor

# Инициализация базы данных
conn, cursor = setup_database()

# Класс для управления состояниями бота
class BotStates(StatesGroup):
    waiting_for_feedback = State()
    waiting_for_admin_username = State()
    waiting_for_reply = State()
    feedback_type = State()
    waiting_for_admin_id = State()

# Инициализация бота и диспетчера с хранилищем состояний
storage = MemoryStorage()
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=storage)

# Проверка, является ли пользователь администратором
async def is_admin(user_id):
    cursor.execute("SELECT 1 FROM admins WHERE user_id = ?", (user_id,))
    return cursor.fetchone() is not None

# Создаем клавиатуру для пользователей
def get_user_keyboard():
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="❓ Задать вопрос", callback_data="feedback_question"))
    builder.add(InlineKeyboardButton(text="⚠️ Сообщить о проблеме", callback_data="feedback_problem"))
    builder.add(InlineKeyboardButton(text="💡 Обратиться с инициативой", callback_data="feedback_initiative"))
    builder.adjust(1)  # Одна кнопка в ряд
    return builder.as_markup()

# Создаем клавиатуру для администраторов
def get_admin_keyboard():
    kb = ReplyKeyboardBuilder()
    kb.add(KeyboardButton(text="➕ Добавить админа"))
    kb.add(KeyboardButton(text="📋 Последние сообщения"))
    kb.adjust(2)  # Два элемента в ряду
    return kb.as_markup(resize_keyboard=True)

# Обработчик команды /start
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    """Отправляет приветственное сообщение и создает клавиатуру."""
    user_id = message.from_user.id
    logger.info(f"Пользователь {user_id} запустил бота")
    
    # Проверяем, является ли пользователь администратором
    if await is_admin(user_id):
        await message.answer(
            "👋 Здравствуйте, администратор! Используйте меню ниже для управления ботом.",
            reply_markup=get_admin_keyboard()
        )
    else:
        await message.answer(
            "Здравствуйте!\n\n"
            "Этот бот создан, чтобы сделать наше общение максимально удобным и эффективным. "
            "Здесь нет посредников — ваше обращение попадает напрямую ко мне и моей команде.\n\n"
            "С уважением, сенатор Олег Евгеньевич Голов.\n\n"
            "Пожалуйста, выберите нужный пункт меню, чтобы продолжить:",
            reply_markup=get_user_keyboard()
        )

# Обработчики нажатия на кнопки выбора типа обращения
@dp.callback_query(F.data == "feedback_question")
async def process_feedback_question(callback_query: types.CallbackQuery, state: FSMContext):
    """Обрабатывает нажатие на кнопку вопроса."""
    await callback_query.answer()
    logger.info(f"Пользователь {callback_query.from_user.id} выбрал тип 'Вопрос'")
    
    await state.update_data(feedback_type="question")
    
    # Отправляем сообщение с просьбой написать обращение
    await callback_query.message.edit_text(
        "❓ Пожалуйста, напишите ваш вопрос в одном сообщении."
    )
    
    # Устанавливаем состояние ожидания сообщения
    await state.set_state(BotStates.waiting_for_feedback)
    logger.info(f"Установлено состояние waiting_for_feedback для пользователя {callback_query.from_user.id}")

@dp.callback_query(F.data == "feedback_problem")
async def process_feedback_problem(callback_query: types.CallbackQuery, state: FSMContext):
    """Обрабатывает нажатие на кнопку проблемы."""
    await callback_query.answer()
    logger.info(f"Пользователь {callback_query.from_user.id} выбрал тип 'Проблема'")
    
    await state.update_data(feedback_type="problem")
    
    # Отправляем сообщение с просьбой написать обращение
    await callback_query.message.edit_text(
        "⚠️ Пожалуйста, опишите вашу проблему в одном сообщении."
    )
    
    # Устанавливаем состояние ожидания сообщения
    await state.set_state(BotStates.waiting_for_feedback)
    logger.info(f"Установлено состояние waiting_for_feedback для пользователя {callback_query.from_user.id}")

@dp.callback_query(F.data == "feedback_initiative")
async def process_feedback_initiative(callback_query: types.CallbackQuery, state: FSMContext):
    """Обрабатывает нажатие на кнопку инициативы."""
    await callback_query.answer()
    logger.info(f"Пользователь {callback_query.from_user.id} выбрал тип 'Инициатива'")
    
    await state.update_data(feedback_type="initiative")
    
    # Отправляем сообщение с просьбой написать обращение
    await callback_query.message.edit_text(
        "💡 Пожалуйста, опишите вашу инициативу в одном сообщении."
    )
    
    # Устанавливаем состояние ожидания сообщения
    await state.set_state(BotStates.waiting_for_feedback)
    logger.info(f"Установлено состояние waiting_for_feedback для пользователя {callback_query.from_user.id}")

# Обработчик текстовых сообщений в состоянии ожидания обратной связи
@dp.message(StateFilter(BotStates.waiting_for_feedback))
async def handle_feedback_message(message: types.Message, state: FSMContext):
    """Обрабатывает сообщение с обратной связью."""
    # Получаем данные пользователя
    user_id = message.from_user.id
    username = message.from_user.username or "Нет юзернейма"
    first_name = message.from_user.first_name or "Нет имени"
    last_name = message.from_user.last_name or "Нет фамилии"
    message_text = message.text
    
    # Получаем тип обращения из состояния
    state_data = await state.get_data()
    feedback_type = state_data.get("feedback_type", "не указан")
    
    logger.info(f"Получено сообщение от пользователя {user_id} ({username}), тип: {feedback_type}")
    
    # Конвертируем тип обращения в читаемый формат
    feedback_type_readable = "Вопрос"
    if feedback_type == "problem":
        feedback_type_readable = "Проблема"
    elif feedback_type == "initiative":
        feedback_type_readable = "Инициатива"
    
    # Сохраняем сообщение в базе данных
    cursor.execute(
        "INSERT INTO feedback (user_id, username, first_name, last_name, message, feedback_type) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, username, first_name, last_name, message_text, feedback_type)
    )
    conn.commit()
    
    # Получаем ID только что добавленной записи
    feedback_id = cursor.lastrowid
    logger.info(f"Сообщение сохранено в базе данных с ID {feedback_id}")
    
    # Отправляем подтверждение пользователю
    await message.answer(
        "Спасибо! Ваше сообщение получено."
    )
    
    # Отправляем сообщение всем администраторам
    cursor.execute("SELECT user_id FROM admins")
    admins = cursor.fetchall()
    
    # Создаем клавиатуру для ответа на сообщение
    reply_kb = InlineKeyboardBuilder()
    reply_kb.add(InlineKeyboardButton(text="✏️ Ответить", callback_data=f"reply_{feedback_id}"))
    reply_kb.add(InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"delete_{feedback_id}"))
    
    for admin in admins:
        admin_id = admin[0]
        try:
            await bot.send_message(
                chat_id=admin_id,
                text=f"📨 Новое обращение #{feedback_id}:\n\n"
                     f"Тип: {feedback_type_readable}\n"
                     f"От: {first_name} {last_name} (@{username})\n"
                     f"ID пользователя: {user_id}\n\n"
                     f"Сообщение:\n{message_text}",
                reply_markup=reply_kb.as_markup()
            )
            logger.info(f"Уведомление отправлено администратору {admin_id}")
        except Exception as e:
            logger.error(f"Не удалось отправить сообщение администратору {admin_id}: {e}")
    
    # Сбрасываем состояние
    await state.clear()
    logger.info(f"Состояние сброшено для пользователя {user_id}")
    
    # Возвращаем пользователя в меню /start
    await asyncio.sleep(1)  # Небольшая задержка для лучшего UX
    
    # Проверяем, является ли пользователь администратором
    if await is_admin(user_id):
        await message.answer(
            "👋 Здравствуйте, администратор! Используйте меню ниже для управления ботом.",
            reply_markup=get_admin_keyboard()
        )
    else:
        await message.answer(
            "Здравствуйте!\n\n"
            "Этот бот создан, чтобы сделать наше общение максимально удобным и эффективным. "
            "Здесь нет посредников — ваше обращение попадает напрямую ко мне и моей команде.\n\n"
            "С уважением, сенатор Олег Евгеньевич Голов.\n\n"
            "Пожалуйста, выберите нужный пункт меню, чтобы продолжить:",
            reply_markup=get_user_keyboard()
        )

# Обработчик для просмотра последних сообщений
@dp.message(F.text == "📋 Последние сообщения", StateFilter(None))
async def show_recent_messages(message: types.Message):
    """Показывает последние 5 сообщений."""
    user_id = message.from_user.id
    
    # Проверяем, является ли пользователь администратором
    if not await is_admin(user_id):
        await message.answer("❌ У вас нет прав администратора.")
        return
    
    logger.info(f"Администратор {user_id} запросил просмотр последних сообщений")
    
    try:
        # Показываем последние 5 сообщений
        cursor.execute(
            """
            SELECT id, user_id, username, first_name, last_name, message, timestamp, is_replied, feedback_type 
            FROM feedback 
            ORDER BY timestamp DESC 
            LIMIT 5
            """
        )
        messages = cursor.fetchall()
        
        if not messages:
            await message.answer("📭 Нет сообщений для отображения. Пока никто не отправил обращений.")
            return
        
        for msg in messages:
            msg_id, user_id, username, first_name, last_name, msg_text, timestamp, is_replied, feedback_type = msg
            status = "✅ Отвечено" if is_replied else "⏳ Ожидает ответа"
            
            # Определяем тип обращения (для старых сообщений будет "Не указан")
            feedback_type_readable = "Не указан"
            if feedback_type == "problem":
                feedback_type_readable = "Проблема"
            elif feedback_type == "initiative":
                feedback_type_readable = "Инициатива"
            
            # Создаем клавиатуру для каждого сообщения
            kb = InlineKeyboardBuilder()
            kb.add(InlineKeyboardButton(text="✏️ Ответить", callback_data=f"reply_{msg_id}"))
            kb.add(InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"delete_{msg_id}"))
            
            await message.answer(
                f"📨 Сообщение #{msg_id}:\n"
                f"Тип: {feedback_type_readable}\n"
                f"От: {first_name} {last_name} (@{username})\n"
                f"ID пользователя: {user_id}\n"
                f"Дата: {timestamp}\n"
                f"Статус: {status}\n\n"
                f"Сообщение:\n{msg_text}",
                reply_markup=kb.as_markup()
            )
    except sqlite3.Error as e:
        logger.error(f"Ошибка при получении сообщений: {e}")
        await message.answer(f"❌ Произошла ошибка при получении сообщений: {e}")

# Обработчик обычных сообщений (вне состояний)
@dp.message(StateFilter(None), ~F.text.in_(["➕ Добавить админа", "📋 Последние сообщения"]), ~F.text.startswith("/"))
async def handle_general_messages(message: types.Message):
    """Обрабатывает обычные сообщения вне состояний."""
    user_id = message.from_user.id
    
    # Проверяем, является ли пользователь администратором
    if await is_admin(user_id):
        logger.info(f"Получено обычное сообщение от администратора {user_id}")
        await message.answer("Используйте меню для управления ботом:", reply_markup=get_admin_keyboard())
    else:
        logger.info(f"Получено обычное сообщение от пользователя {user_id}")
        await message.answer(
            "Для отправки обращения, пожалуйста, используйте меню ниже:",
            reply_markup=get_user_keyboard()
        )

# Обработчик для добавления админа через текстовую кнопку
@dp.message(F.text == "➕ Добавить админа", StateFilter(None))
async def start_add_admin(message: types.Message, state: FSMContext):
    """Начинает процесс добавления нового администратора."""
    user_id = message.from_user.id
    
    # Проверяем, является ли пользователь администратором
    if not await is_admin(user_id):
        await message.answer("❌ У вас нет прав администратора.")
        return
    
    logger.info(f"Администратор {user_id} начал процесс добавления нового администратора")
    await message.answer("Для добавления нового администратора, перешлите сообщение от пользователя, которого хотите сделать администратором, или отправьте его ID.")
    await state.set_state(BotStates.waiting_for_admin_id)
    logger.info(f"Установлено состояние waiting_for_admin_id для пользователя {user_id}")

# Обработчик для пересланных сообщений или ID для добавления администратора
@dp.message(StateFilter(BotStates.waiting_for_admin_id))
async def handle_admin_id_message(message: types.Message, state: FSMContext):
    """Обрабатывает сообщение с ID нового администратора."""
    current_admin_id = message.from_user.id
    
    # Проверяем, является ли текущий пользователь администратором
    if not await is_admin(current_admin_id):
        await message.answer("У вас нет прав администратора.")
        return
    
    # Получаем ID нового администратора
    new_admin_id = None
    new_admin_username = None
    
    if message.forward_from:
        # Если сообщение переслано, получаем ID из пересланного сообщения
        new_admin_id = message.forward_from.id
        new_admin_username = message.forward_from.username
        logger.info(f"Получен ID нового администратора из пересланного сообщения: {new_admin_id}")
    else:
        # Иначе пытаемся распарсить ID из текста сообщения
        try:
            new_admin_id = int(message.text.strip())
            logger.info(f"Получен ID нового администратора из текста: {new_admin_id}")
        except ValueError:
            await message.answer(
                "❌ Не удалось распознать ID пользователя. Пожалуйста, перешлите сообщение от пользователя "
                "или отправьте его числовой ID."
            )
            return
    
    # Проверяем, не является ли пользователь уже администратором
    cursor.execute("SELECT * FROM admins WHERE user_id = ?", (new_admin_id,))
    existing_admin = cursor.fetchone()
    
    if existing_admin:
        await message.answer(f"❌ Пользователь с ID {new_admin_id} уже является администратором.")
        # Сбрасываем состояние и возвращаем админское меню
        await state.clear()
        await message.answer(
            "👋 Здравствуйте, администратор! Используйте меню ниже для управления ботом.",
            reply_markup=get_admin_keyboard()
        )
        return
    
    # Добавляем нового администратора в базу данных
    try:
        cursor.execute(
            "INSERT INTO admins (user_id, username, added_by) VALUES (?, ?, ?)",
            (new_admin_id, new_admin_username, current_admin_id)
        )
        conn.commit()
        logger.info(f"Добавлен новый администратор: {new_admin_id}")
        
        await message.answer(f"✅ Пользователь с ID {new_admin_id} успешно добавлен как администратор.")
        
        # Отправляем уведомление новому администратору
        try:
            await bot.send_message(
                chat_id=new_admin_id,
                text="🎉 Вам были предоставлены права администратора в боте обратной связи."
            )
            logger.info(f"Отправлено уведомление новому администратору {new_admin_id}")
        except Exception as e:
            logger.error(f"Не удалось отправить уведомление новому администратору {new_admin_id}: {e}")
    
    except Exception as e:
        logger.error(f"Ошибка при добавлении администратора: {e}")
        await message.answer(f"❌ Произошла ошибка при добавлении администратора: {e}")
    
    # Сбрасываем состояние и возвращаем админское меню
    await state.clear()
    await message.answer(
        "👋 Здравствуйте, администратор! Используйте меню ниже для управления ботом.",
        reply_markup=get_admin_keyboard()
    )

# Обработчик команды /admin для установки ID администратора
@dp.message(Command("admin"))
async def cmd_admin(message: types.Message):
    """Устанавливает пользователя как администратора, если он еще не является администратором."""
    user_id = message.from_user.id
    username = message.from_user.username
    
    logger.info(f"Пользователь {user_id} выполнил команду /admin")
    
    # Проверяем, не является ли пользователь уже администратором
    cursor.execute("SELECT 1 FROM admins WHERE user_id = ?", (user_id,))
    if cursor.fetchone():
        logger.info(f"Пользователь {user_id} уже является администратором")
        await message.answer(
            f"❌ Вы уже являетесь администратором бота.\n"
            f"Используйте команду /unadmin, если вы хотите отказаться от прав администратора.",
            reply_markup=get_admin_keyboard()
        )
        return
    
    # Добавляем пользователя как администратора
    cursor.execute(
        "INSERT INTO admins (user_id, username) VALUES (?, ?)", 
        (user_id, username)
    )
    conn.commit()
    logger.info(f"Пользователь {user_id} добавлен как администратор")
    
    await message.answer(
        f"✅ Вы были добавлены как администратор бота!\n"
        f"Ваш ID: {user_id}\n\n"
        f"Теперь вы будете получать все обращения, отправленные через бот.",
        reply_markup=get_admin_keyboard()
    )

# Обработчик команды /unadmin для удаления прав администратора
@dp.message(Command("unadmin"))
async def cmd_unadmin(message: types.Message):
    """Удаляет пользователя из списка администраторов."""
    user_id = message.from_user.id
    
    logger.info(f"Пользователь {user_id} выполнил команду /unadmin")
    
    # Проверяем, является ли пользователь администратором
    cursor.execute("SELECT 1 FROM admins WHERE user_id = ?", (user_id,))
    if not cursor.fetchone():
        logger.info(f"Пользователь {user_id} не является администратором")
        await message.answer(
            f"❌ Вы не являетесь администратором бота.\n"
            f"Используйте команду /admin, если вы хотите стать администратором."
        )
        return
    
    # Удаляем пользователя из списка администраторов
    cursor.execute("DELETE FROM admins WHERE user_id = ?", (user_id,))
    conn.commit()
    logger.info(f"Пользователь {user_id} удален из списка администраторов")
    
    await message.answer(
        f"✅ Вы были удалены из списка администраторов бота.\n"
        f"Теперь вы больше не будете получать обращения от пользователей."
    )

# Обработчик команды /unadm для удаления прав администратора (альтернативная команда)
@dp.message(Command("unadm"))
async def cmd_unadm(message: types.Message):
    """Альтернативная команда для удаления пользователя из списка администраторов."""
    user_id = message.from_user.id
    
    logger.info(f"Пользователь {user_id} выполнил команду /unadm")
    
    # Проверяем, является ли пользователь администратором
    cursor.execute("SELECT 1 FROM admins WHERE user_id = ?", (user_id,))
    if not cursor.fetchone():
        logger.info(f"Пользователь {user_id} не является администратором")
        await message.answer(
            f"❌ Вы не являетесь администратором бота.\n"
            f"Используйте команду /admin, если вы хотите стать администратором."
        )
        return
    
    # Удаляем пользователя из списка администраторов
    cursor.execute("DELETE FROM admins WHERE user_id = ?", (user_id,))
    conn.commit()
    logger.info(f"Пользователь {user_id} удален из списка администраторов")
    
    await message.answer(
        f"✅ Вы были удалены из списка администраторов бота.\n"
        f"Теперь вы больше не будете получать обращения от пользователей."
    )

# Специальный обработчик для команд /unadmin и /unadm
@dp.message(F.text.in_(["/unadmin", "/unadm"]))
async def cmd_unadmin_direct(message: types.Message):
    """Удаляет пользователя из списка администраторов. Прямой обработчик текста команды."""
    user_id = message.from_user.id
    
    logger.info(f"Пользователь {user_id} выполнил команду {message.text}")
    
    # Проверяем, является ли пользователь администратором
    cursor.execute("SELECT 1 FROM admins WHERE user_id = ?", (user_id,))
    if not cursor.fetchone():
        logger.info(f"Пользователь {user_id} не является администратором")
        await message.answer(
            f"❌ Вы не являетесь администратором бота.\n"
            f"Используйте команду /admin, если вы хотите стать администратором."
        )
        return
    
    # Удаляем пользователя из списка администраторов
    cursor.execute("DELETE FROM admins WHERE user_id = ?", (user_id,))
    conn.commit()
    logger.info(f"Пользователь {user_id} удален из списка администраторов")
    
    await message.answer(
        f"✅ Вы были удалены из списка администраторов бота.\n"
        f"Теперь вы больше не будете получать обращения от пользователей."
    )

# Обработчик нажатия на кнопку ответа
@dp.callback_query(lambda c: c.data and c.data.startswith('reply_'))
async def process_reply_button(callback_query: types.CallbackQuery, state: FSMContext):
    """Обрабатывает нажатие на кнопку ответа на сообщение."""
    await callback_query.answer()
    
    # Получаем ID сообщения из callback_data
    feedback_id = int(callback_query.data.split('_')[1])
    logger.info(f"Запрошен ответ на сообщение ID: {feedback_id}")
    
    # Сохраняем ID сообщения в состоянии
    await state.update_data(feedback_id=feedback_id)
    
    # Получаем информацию о сообщении
    cursor.execute(
        "SELECT user_id, username, first_name, last_name, message FROM feedback WHERE id = ?",
        (feedback_id,)
    )
    feedback_data = cursor.fetchone()
    
    if feedback_data:
        user_id, username, first_name, last_name, message_text = feedback_data
        logger.info(f"Найдено сообщение ID {feedback_id} от пользователя {first_name} {last_name}")
        
        await callback_query.message.answer(
            f"💬 Введите ответ на сообщение #{feedback_id} от {first_name} {last_name} (@{username}):\n\n"
            f"Исходное сообщение:\n{message_text}"
        )
        
        # Устанавливаем состояние ожидания ответа
        await state.set_state(BotStates.waiting_for_reply)
        logger.info(f"Установлено состояние ожидания ответа для пользователя {callback_query.from_user.id}")
    else:
        logger.error(f"Сообщение ID {feedback_id} не найдено в базе данных")
        await callback_query.message.answer("❌ Сообщение не найдено.")

# Обработчик нажатия на кнопку удаления сообщения
@dp.callback_query(lambda c: c.data and c.data.startswith('delete_'))
async def process_delete_button(callback_query: types.CallbackQuery):
    """Обрабатывает нажатие на кнопку удаления сообщения."""
    await callback_query.answer()
    
    # Получаем ID сообщения из callback_data
    feedback_id = int(callback_query.data.split('_')[1])
    logger.info(f"Запрошено удаление сообщения ID: {feedback_id}")
    
    # Удаляем сообщение из базы данных
    cursor.execute("DELETE FROM feedback WHERE id = ?", (feedback_id,))
    conn.commit()
    logger.info(f"Сообщение ID {feedback_id} удалено из базы данных")
    
    await callback_query.message.answer(f"✅ Сообщение #{feedback_id} удалено.")

# Обработчик ввода текста ответа
@dp.message(StateFilter(BotStates.waiting_for_reply))
async def process_reply_text(message: types.Message, state: FSMContext):
    """Обрабатывает ввод текста ответа на сообщение."""
    admin_id = message.from_user.id
    reply_text = message.text
    logger.info(f"Обработка ответа от администратора {admin_id}: '{reply_text}'")
    
    # Получаем ID сообщения из состояния
    data = await state.get_data()
    feedback_id = data.get('feedback_id')
    logger.info(f"ID сообщения из состояния: {feedback_id}")
    
    if not feedback_id:
        logger.error("ID сообщения не найден в состоянии")
        await message.answer("❌ Ошибка: не найден ID сообщения. Пожалуйста, попробуйте еще раз.")
        await state.clear()
        await message.answer("Выберите действие:", reply_markup=get_admin_keyboard())
        return
    
    # Получаем информацию о пользователе, отправившем сообщение
    cursor.execute("SELECT user_id, first_name, last_name FROM feedback WHERE id = ?", (feedback_id,))
    feedback_data = cursor.fetchone()
    
    if feedback_data:
        user_id, first_name, last_name = feedback_data
        logger.info(f"Отправка ответа пользователю {user_id} на сообщение {feedback_id}")
        
        # Сохраняем ответ в базе данных
        try:
            cursor.execute(
                "INSERT INTO replies (feedback_id, admin_id, reply_text) VALUES (?, ?, ?)",
                (feedback_id, admin_id, reply_text)
            )
            
            # Обновляем статус сообщения (отвечено)
            cursor.execute("UPDATE feedback SET is_replied = 1 WHERE id = ?", (feedback_id,))
            conn.commit()
            logger.info(f"Ответ сохранен в базе данных, статус сообщения обновлен")
            
            # Отправляем ответ пользователю
            try:
                await bot.send_message(
                    chat_id=user_id,
                    text=f"📩 Ответ на ваше обращение #{feedback_id}:\n\n{reply_text}"
                )
                logger.info(f"Ответ успешно отправлен пользователю {user_id}")
                
                await message.answer(f"✅ Ваш ответ успешно отправлен пользователю {first_name} {last_name}.")
            except Exception as e:
                logger.error(f"Не удалось отправить ответ пользователю {user_id}: {e}")
                await message.answer(f"❌ Не удалось отправить ответ пользователю. Возможно, пользователь заблокировал бота. Ошибка: {e}")
        except Exception as e:
            logger.error(f"Ошибка при сохранении ответа в базе данных: {e}")
            await message.answer(f"❌ Ошибка при сохранении ответа: {e}")
    else:
        logger.error(f"Сообщение ID {feedback_id} не найдено при попытке ответа")
        await message.answer("❌ Сообщение не найдено.")
    
    # Сбрасываем состояние
    await state.clear()
    logger.info(f"Состояние сброшено после обработки ответа")
    
    # Возвращаем клавиатуру администратора
    await message.answer("Выберите действие:", reply_markup=get_admin_keyboard())

# Главная функция
async def main():
    """Запускает бота."""
    # Запускаем бота
    await dp.start_polling(bot, skip_updates=True)

if __name__ == '__main__':
    asyncio.run(main())
