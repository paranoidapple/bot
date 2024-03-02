import sys
import os

sys.path.append(os.path.abspath('.'))  # Terminal compatibility

import uvloop
from dotenv import load_dotenv

from src.models.bot import Bot

uvloop.install()
load_dotenv()

bot = Bot(token=os.environ["TOKEN"])
bot.run()
