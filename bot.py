import asyncio
import logging

from maxapi import Bot, Dispatcher, F
from maxapi.types import (
    BotStarted,
    MessageCreated,
    MessageCallback,
    Command,
    CallbackButton,
)
from maxapi.context import MemoryContext, State, StatesGroup
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder

from config import BOT_TOKEN, MANAGER_CHAT_ID

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


class ReportStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_location = State()
    waiting_for_date = State()
    waiting_for_result = State()
    waiting_for_participants = State()
    waiting_for_description = State()
    waiting_for_link = State()
    waiting_for_photo = State()


CATEGORY_NAMES_FIELD = {
    "gto": "ГТО",
    "sections": "Секции",
    "recreational_trips": "Физкультурно-оздоровительные выезды",
    "district_teams": "Сборная района, команды ЦФКСиЗ, иные турниры",
}

CATEGORY_DISTRICT = {
    "opsmm": "ОПСММ",
    "gto_d": "ГТО",
    "sections_d": "СЕКЦИИ",
    "yard_playgrounds": "Внутредворовые площадки",
    "rdm": "РДМ",
}

CATEGORY_SPART = {
    "rdm_sp": "РДМ",
    "ovz": "ОВЗ",
    "kdn": "КДН",
    "silver_age": "Серебрянный возраст",
    "family_teams": "Семейные команды",
    "work_collectives": "Трудовые коллективы",
}


def make_kb(buttons: list[list[tuple[str, str]]]) -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    for row in buttons:
        btns = [CallbackButton(text=text, payload=payload) for text, payload in row]
        builder.row(*btns)
    return builder


def get_user_info(event) -> str:
    chat = getattr(event, 'chat', None)
    if not chat:
        return "Неизвестно"
    name = getattr(chat, 'title', None) or f"{getattr(chat, 'first_name', '') or ''} {getattr(chat, 'last_name', '') or ''}".strip()
    return name or "Неизвестно"


def is_image_attachment(att) -> bool:
    t = getattr(att, "type", None)
    if t is None and isinstance(att, dict):
        t = att.get("type")
    return str(t).lower() == "image"


async def finalize_report(event: MessageCreated, context: MemoryContext):
    data = await context.get_data()
    photos = data.get("photos", []) or []
    photo_count = len(photos)

    sender = getattr(event.message, "sender", None) or getattr(event, "chat", None) or getattr(event.message, "chat", None)
    if sender:
        first = getattr(sender, "first_name", "") or ""
        last = getattr(sender, "last_name", "") or ""
        username = getattr(sender, "username", "") or ""
        user_info = f"{first} {last}".strip()
        if username:
            user_info += f" (@{username})"
    else:
        user_info = "Неизвестно"

    event_type = data.get("type", "Не указано")
    category = data.get("category", "Не указано")
    sub_category = data.get("sub_category", "")

    if sub_category:
        category_full = f"{event_type} → {category} → {sub_category}"
    elif category:
        category_full = f"{event_type} → {category}"
    else:
        category_full = event_type

    report = f"""
✅ Отчет заполнен успешно!

📍 Категория: {category_full}

📋 Информация о мероприятии:

1️⃣ Название: {data.get('name', 'Не указано')}
2️⃣ Место проведения: {data.get('location', 'Не указано')}
3️⃣ Дата проведения: {data.get('date', 'Не указано')}
4️⃣ Результат: {data.get('result', 'Не указано')}
5️⃣ Количество участников: {data.get('participants', 'Не указано')}
6️⃣ Краткое описание: {data.get('description', 'Не указано')}
7️⃣ Ссылка: {data.get('link', 'Не указано')}
8️⃣ Фото: {'Приложено ' + str(photo_count) + ' шт.' if photo_count else 'Не приложено'}

👤 Ответственный/заполнитель: {user_info}
"""

    attachments = list(photos) if photos else []

    await event.message.answer(text=report, attachments=attachments if attachments else None)

    if MANAGER_CHAT_ID:
        try:
            mgr_attachments = list(photos) if photos else None
            resp = await bot.send_message(
                chat_id=MANAGER_CHAT_ID,
                text=report,
                attachments=mgr_attachments,
            )
            logger.info(f"Отправлено руководителю, ответ: {resp}")
        except Exception as e:
            logger.warning(f"Не удалось отправить руководителю: {e}")

    await context.clear()

    builder = make_kb([
        [("Создать новый отчет", "create_report")],
    ])
    await event.message.answer(
        text="Хотите создать еще один отчет?",
        attachments=[builder.as_markup()],
    )


@dp.bot_started()
async def on_bot_started(event: BotStarted):
    """Когда пользователь впервые нажимает Старт в диалоге с ботом"""
    builder = make_kb([
        [("Создать отчет", "create_report")],
    ])
    name = event.chat.first_name or ""
    await bot.send_message(
        chat_id=event.chat.id,
        text=f"Привет, {name}!\nЧто будем делать?",
        attachments=[builder.as_markup()],
    )


@dp.message_created(Command("start"))
async def cmd_start(event: MessageCreated):
    builder = make_kb([
        [("Создать отчет", "create_report")],
    ])
    name = getattr(event.chat, 'first_name', '') or ""
    await event.message.answer(
        text=f"Привет, {name}!\nЧто будем делать?",
        attachments=[builder.as_markup()],
    )


@dp.message_created(Command("help"))
async def cmd_help(event: MessageCreated):
    await event.message.answer(text="""
Доступные команды:
/start - Начать работу с ботом
/help - Показать это сообщение
/menu - Показать меню
""")


@dp.message_created(Command("menu"))
async def cmd_menu(event: MessageCreated):
    builder = make_kb([
        [("Создать отчет", "create_report")],
    ])
    await event.message.answer(
        text="Выберите действие:",
        attachments=[builder.as_markup()],
    )


@dp.message_callback()
async def handle_callbacks(event: MessageCallback, context: MemoryContext):
    payload = event.callback.payload

    if payload == "create_report":
        builder = make_kb([
            [("Выездные мероприятия", "field_events")],
            [("Районные", "district_events")],
        ])
        await event.answer(new_text=".")
        await event.message.answer(
            text="Выберите тип мероприятия:",
            attachments=[builder.as_markup()],
        )

    elif payload == "field_events":
        builder = make_kb([
            [("ГТО", "field_events:gto")],
            [("Секции", "field_events:sections")],
            [("Физкультурно-оздоровительные выезды", "field_events:recreational_trips")],
            [("Сборная района, команды ЦФКСиЗ, иные турниры", "field_events:district_teams")],
            [("Спартакиады", "spartakiads")],
            [("↩️ Вернуться", "create_report")],
        ])
        await event.answer(new_text=".")
        await event.message.answer(
            text="Выберите категорию выездного мероприятия:",
            attachments=[builder.as_markup()],
        )

    elif payload == "district_events":
        builder = make_kb([
            [("ОПСММ", "district_events:opsmm")],
            [("ГТО", "district_events:gto_d")],
            [("СЕКЦИИ", "district_events:sections_d")],
            [("Внутредворовые площадки", "district_events:yard_playgrounds")],
            [("РДМ", "district_events:rdm")],
            [("↩️ Вернуться", "create_report")],
        ])
        await event.answer(new_text=".")
        await event.message.answer(
            text="Выберите категорию районного мероприятия:",
            attachments=[builder.as_markup()],
        )

    elif payload == "spartakiads":
        builder = make_kb([
            [("РДМ", "spart:rdm_sp")],
            [("ОВЗ", "spart:ovz")],
            [("КДН", "spart:kdn")],
            [("Серебрянный возраст", "spart:silver_age")],
            [("Семейные команды", "spart:family_teams")],
            [("Трудовые коллективы", "spart:work_collectives")],
            [("↩️ Вернуться", "field_events")],
        ])
        await event.answer(new_text=".")
        await event.message.answer(
            text="Выберите вид спартакиады:",
            attachments=[builder.as_markup()],
        )

    elif payload.startswith("field_events:"):
        sub = payload.split(":", 1)[1]
        name = CATEGORY_NAMES_FIELD.get(sub, sub.replace("_", " ").title())
        await context.update_data(
            category=name,
            type="Выездные мероприятия",
        )
        await event.answer(new_text=f"✅ {name}")
        await event.message.answer(
            text=f"✅ Выбрано: {name}\n\n"
            "Пожалуйста, ответьте на несколько вопросов:\n\n"
            "1️⃣ Название мероприятия\n"
            "Введите название мероприятия:"
        )
        await context.set_state(ReportStates.waiting_for_name)

    elif payload.startswith("district_events:"):
        sub = payload.split(":", 1)[1]
        name = CATEGORY_DISTRICT.get(sub, sub.replace("_", " ").title())
        await context.update_data(
            category=name,
            type="Районные",
        )
        await event.answer(new_text=f"✅ {name}")
        await event.message.answer(
            text=f"✅ Выбрано: {name}\n\n"
            "Пожалуйста, ответьте на несколько вопросов:\n\n"
            "1️⃣ Название мероприятия\n"
            "Введите название мероприятия:"
        )
        await context.set_state(ReportStates.waiting_for_name)

    elif payload.startswith("spart:"):
        sub = payload.split(":", 1)[1]
        name = CATEGORY_SPART.get(sub, sub.replace("_", " ").title())
        await context.update_data(
            category="Спартакиады",
            sub_category=name,
            type="Выездные мероприятия",
        )
        await event.answer(new_text=f"✅ Спартакиады → {name}")
        await event.message.answer(
            text=f"✅ Выбрано: Спартакиады → {name}\n\n"
            "Пожалуйста, ответьте на несколько вопросов:\n\n"
            "1️⃣ Название мероприятия\n"
            "Введите название мероприятия:"
        )
        await context.set_state(ReportStates.waiting_for_name)

    elif payload == "skip_link":
        await context.update_data(link="Не указано", photos=[])
        await context.set_state(ReportStates.waiting_for_photo)
        await event.answer(new_text="Ссылка пропущена")
        await event.message.answer(
            text="✅ Ссылка: Не указано\n\n"
            "8️⃣ Фото\n"
            "Отправьте до 10 фотографий мероприятия по очереди.\n"
            "По завершении напишите 'готово' или 'пропустить' для пропуска."
        )

    else:
        try:
            await event.answer(new_text=".")
        except Exception:
            pass


@dp.message_created(F.message.body.text, ReportStates.waiting_for_name)
async def process_name(event: MessageCreated, context: MemoryContext):
    name = event.message.body.text
    await context.update_data(name=name)
    await context.set_state(ReportStates.waiting_for_location)
    await event.message.answer(
        text=f"✅ Название: {name}\n\n"
        "2️⃣ Место проведения\n"
        "Введите место проведения мероприятия:"
    )


@dp.message_created(F.message.body.text, ReportStates.waiting_for_location)
async def process_location(event: MessageCreated, context: MemoryContext):
    location = event.message.body.text
    await context.update_data(location=location)
    await context.set_state(ReportStates.waiting_for_date)
    await event.message.answer(
        text=f"✅ Место проведения: {location}\n\n"
        "3️⃣ Дата проведения\n"
        "Введите дату проведения (например, 25.10.2024):"
    )


@dp.message_created(F.message.body.text, ReportStates.waiting_for_date)
async def process_date(event: MessageCreated, context: MemoryContext):
    date = event.message.body.text
    await context.update_data(date=date)
    await context.set_state(ReportStates.waiting_for_result)
    await event.message.answer(
        text=f"✅ Дата проведения: {date}\n\n"
        "4️⃣ Результат\n"
        "Опишите результат мероприятия:"
    )


@dp.message_created(F.message.body.text, ReportStates.waiting_for_result)
async def process_result(event: MessageCreated, context: MemoryContext):
    result = event.message.body.text
    await context.update_data(result=result)
    await context.set_state(ReportStates.waiting_for_participants)
    await event.message.answer(
        text=f"✅ Результат: {result}\n\n"
        "5️⃣ Количество участников\n"
        "Введите количество участников (число):"
    )


@dp.message_created(F.message.body.text, ReportStates.waiting_for_participants)
async def process_participants(event: MessageCreated, context: MemoryContext):
    participants = event.message.body.text
    await context.update_data(participants=participants)
    await context.set_state(ReportStates.waiting_for_description)
    await event.message.answer(
        text=f"✅ Количество участников: {participants}\n\n"
        "6️⃣ Краткое описание\n"
        "Введите краткое описание мероприятия:"
    )


@dp.message_created(F.message.body.text, ReportStates.waiting_for_description)
async def process_description(event: MessageCreated, context: MemoryContext):
    description = event.message.body.text
    await context.update_data(description=description)
    await context.set_state(ReportStates.waiting_for_link)

    skip_builder = make_kb([
        [("Пропустить", "skip_link")],
    ])
    await event.message.answer(
        text=f"✅ Краткое описание: {description}\n\n"
        "7️⃣ Ссылка на организаторов\n"
        "Введите ссылку ВК или сайт на организаторов (или 'пропустить'):",
        attachments=[skip_builder.as_markup()],
    )


@dp.message_created(F.message.body.text, ReportStates.waiting_for_link)
async def process_link(event: MessageCreated, context: MemoryContext):
    text = event.message.body.text
    link = "Не указано" if text.lower() == "пропустить" else text
    await context.update_data(link=link, photos=[])
    await context.set_state(ReportStates.waiting_for_photo)
    await event.message.answer(
        text=f"✅ Ссылка: {link}\n\n"
        "8️⃣ Фото\n"
        "Отправьте до 10 фотографий мероприятия по очереди.\n"
        "По завершении напишите 'готово' или 'пропустить' для пропуска."
    )


@dp.message_created(ReportStates.waiting_for_photo)
async def process_photo(event: MessageCreated, context: MemoryContext):
    data = await context.get_data()
    photos = data.get("photos", []) or []

    text = getattr(event.message.body, "text", None)
    if text:
        text = text.strip().lower()
        if text == "пропустить":
            if photos:
                await event.message.answer(
                    text="Вы уже добавили фотографии. Напишите 'готово'."
                )
                return
            await context.update_data(photos=[])
            await finalize_report(event, context)
            return

        if text == "готово":
            await context.update_data(photos=photos)
            await finalize_report(event, context)
            return

    attachments = getattr(event.message.body, "attachments", None)
    if attachments:
        has_new_image = False
        for att in attachments:
            if is_image_attachment(att):
                if len(photos) >= 10:
                    await event.message.answer(
                        text="Вы уже загрузили 10 фотографий. Напишите 'готово'."
                    )
                    return
                photos.append(att)
                has_new_image = True
        if has_new_image:
            await context.update_data(photos=photos)
            if len(photos) >= 10:
                await event.message.answer(text="📸 Добавлено 10/10 фото. Напишите 'готово'.")
            else:
                await event.message.answer(
                    text=f"📸 Фото {len(photos)} сохранено. "
                    "Отправьте еще или напишите 'готово'. "
                    "Если хотите завершить без фото, напишите 'пропустить'."
                )
            return

    await event.message.answer(
        text="Пожалуйста, отправьте фото, напишите 'готово' или 'пропустить'."
    )


@dp.message_created()
async def fallback_handler(event: MessageCreated, context: MemoryContext):
    current = await context.get_state()
    if current:
        await event.message.answer(
            text="Пожалуйста, ответьте на текущий вопрос."
        )
    elif event.message.body.text:
        await event.message.answer(text=f"Вы написали: {event.message.body.text}")


async def main():
    logger.info("Запуск бота MAX...")
    await bot.delete_webhook()
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"Ошибка: {e}")