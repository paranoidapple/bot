import uvloop

from dotenv import load_dotenv
from os import environ

from src.models.bot import Bot


uvloop.install()
load_dotenv()

bot = Bot(token=environ["TOKEN"])
bot.run()
