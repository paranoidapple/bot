import hikari
import lightbulb

import os
import aiofiles
import json

import random
import re

from src.models.bot import Bot

quote_generator = lightbulb.Plugin("quote generator")

PROMPTS: dict[int, list[str]] = {}
PROMPTS_DIR = f"{Bot.base_dir}/text/quote_generator/"


@quote_generator.listener(hikari.StartedEvent)
async def create_prompts(_: hikari.StartedEvent):
    """Creates quote prompts."""
    for i, file in enumerate(sorted(os.listdir(PROMPTS_DIR))):
        async with aiofiles.open(PROMPTS_DIR + file, "r") as f:
            prompts = json.loads(await f.read())
            PROMPTS[i + 1] = prompts


@quote_generator.command()
@lightbulb.option(
    name="user1",
    description="The quote's first character, feel free to mention a user.",
    default=None,
)
@lightbulb.option(
    name="user2", description="The quote's second character.", default=None
)
@lightbulb.option(
    name="user3", description="The quote's third character.", default=None
)
@lightbulb.option(
    name="user4", description="The quote's fourth character.", default=None
)
@lightbulb.option(
    name="user5", description="The quote's fifth character.", default=None
)
@lightbulb.option(
    name="user6", description="The quote's sixth character.", default=None
)
@lightbulb.command(
    name="generate-quote",
    description="Generate a (hopefully) funny incorrect quote.",
    auto_defer=True,
)
@lightbulb.implements(lightbulb.SlashCommand)
async def generate_quote(
    ctx: lightbulb.SlashContext,
):
    """COMMAND | Generates a (hopefully) funny incorrect quote."""

    # Parse options
    options = {k: v for k, v in ctx.options.items() if v is not None}
    if not options:
        options = {"user1": ctx.author.mention}

    # Generate random quote
    quote = random.choice(PROMPTS.get(len(options.items())))

    # Replace user placeholders
    for i in range(len(options)):
        quote = quote.replace(
            "{" + chr(65 + i) + "}",
            list(options.values())[i],  # To account for unordered keys (ex. 1, 5)
        )

    # Parse bold, italics, line breaks
    translation = {"<b>": "**", "</b>": "**", "<i>": "*", "</i>": "*", "<br>": "\n"}
    quote = re.compile("|".join(map(re.escape, translation))).sub(
        lambda x: translation[x.group(0)], quote
    )

    return await ctx.respond(
        hikari.Embed(
            title="quote",
            description=quote,
            color=int(hex(random.randrange(0, 2**24)), 16),
        ).set_footer(
            "WARNING: Some prompts may imply shipping between 2 or more characters. This generator is not "
            "meant to imply any adult/minor, abusive, incestuous, or otherwise problematic ships. In the "
            "future I plan to implement a feature to filter out prompts that involve shipping, but until then "
            "I apologize if any prompts try to ship characters that you don't want shipped. -ScatterPatter\n"
            "*Find this generator at https://incorrect-quotes-generator.neocities.org/, all credit goes there.*"
        )
    )


def load(bot: Bot):
    bot.add_plugin(quote_generator)


def unload(bot: Bot):
    bot.remove_plugin(quote_generator)
