
import re

import telepot





telegram_bot = '5953442472:AAHsgzGdcVrnuJnb0FnDWJ4nrPdDT59YNOE'


def send_message(message, telegram_group=None):
    telegramBot = telepot.Bot(telegram_bot)
    telegramBot.sendMessage(telegram_group, message, parse_mode="Markdown")




