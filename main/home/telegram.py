
import re

import telepot





telegram_bot = '5953442472:AAHsgzGdcVrnuJnb0FnDWJ4nrPdDT59YNOE'
telegram_group = '-1002487695898,'

def send_message(message):
    telegramBot = telepot.Bot(telegram_bot)
    telegramBot.sendMessage(telegram_group, message, parse_mode="Markdown")




