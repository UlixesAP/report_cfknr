#!/usr/bin/env python3
"""Проверка доступности MAX API. Запускать из cron."""

import asyncio
import logging
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from config import BOT_TOKEN, MANAGER_CHAT_ID  # noqa: E402
from maxapi import Bot  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger("healthcheck")

MINUTES = 5
THRESHOLD = 3


def count_errors_last(minutes: int) -> int:
    since = f"{minutes} minutes ago"
    result = subprocess.run(
        ["journalctl", "-u", "max-bot", "--since", since, "--no-pager", "-o", "cat"],
        capture_output=True, text=True, timeout=30,
    )
    lines = result.stdout.splitlines()
    count = 0
    for line in lines:
        if any(x in line for x in ("503", "504", "internal.error")):
            count += 1
    return count


async def main():
    errors = count_errors_last(MINUTES)

    try:
        me = await Bot(token=BOT_TOKEN).get_me()
        api_ok = me is not None
    except Exception as e:
        logger.warning("API ping failed: %s", e)
        api_ok = False

    if not api_ok:
        msg = f"MAX API недоступен!"
    elif errors >= THRESHOLD:
        msg = f"MAX API нестабилен: {errors} ошибок за последние {MINUTES} мин."
    else:
        return

    if MANAGER_CHAT_ID:
        try:
            bot = Bot(token=BOT_TOKEN)
            await bot.send_message(chat_id=MANAGER_CHAT_ID, text=msg)
            logger.info("Уведомление отправлено в чат %s", MANAGER_CHAT_ID)
        except Exception as e:
            logger.error("Не удалось отправить уведомление: %s", e)


if __name__ == "__main__":
    asyncio.run(main())