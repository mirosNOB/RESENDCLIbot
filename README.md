# Телеграм-бот для обратной связи

## Описание
Этот телеграм-бот разработан для приема обращений от пользователей. Пользователи могут отправлять свои сообщения через бота, а администраторы получат эти сообщения.

## Функциональность
- Приветственное сообщение при запуске бота
- Кнопка "Отправить обращение" для удобства пользователей
- Сохранение всех обращений в базе данных SQLite
- Автоматическая пересылка обращений администраторам
- Возможность добавления нескольких администраторов

## Настройка
1. Токен бота уже добавлен в код
2. Для добавления себя как администратора, отправьте команду `/admin` боту после его запуска               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/derxywat/.local/lib/python3.13/site-packages/aiogram/dispatcher/event/telegram.py", line 121, in trigger
    return await wrapped_inner(event, kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/derxywat/.local/lib/python3.13/site-packages/aiogram/dispatcher/event/handler.py", line 43, in call
    return await wrapped()
           ^^^^^^^^^^^^^^^
  File "/home/derxywat/CascadeProjects/windsurf-project/feedback_bot.py", line 209, in handle_feedback_message
    cursor.execute(
    ~~~~~~~~~~~~~~^
        "INSERT INTO feedback (user_id, username, first_name, last_name, message, feedback_type) VALUES (?, ?, ?, ?, ?, ?)",
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        (user_id, username, first_name, last_name, message_text, feedback_type)
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
sqlite3.OperationalError: table feedback has no column named feedback_type
2025-03-16 20:00:46,548 - __main__ - INFO - Администратор 7241965595 запросил просмотр последних сообщений
2025-03-16 20:00:46,548 - __main__ - ERROR - Ошибка при получении сообщений: no such column: feedback_type
2025-03-16 20:00:46,655 - aiogram.event - INFO - Update id=907459918 is handled. Duration 108 ms by bot id=8067130497
3. После этого вы будете получать все обращения от пользователей

## Запуск бота
Для запуска бота выполните команду:
```bash
python feedback_bot.py
```

## Безопасность
- Бот использует локальную базу данных SQLite
- Данные защищены и хранятся только на вашем сервере
- Сообщения пользователей доступны только администраторам

## Технические детали
- Бот разработан с использованием библиотеки python-telegram-bot
- Все обращения хранятся в базе данных feedback.db
- В базе сохраняется ID пользователя, имя, фамилия, никнейм и текст обращения
