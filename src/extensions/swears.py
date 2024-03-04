from typing import KeysView

import hikari
import lightbulb

import asyncpg
import aiofiles
import json

from hikari import Message

from src.models.bot import Bot
from src.models.swear import SwearAchievement


swear_counter = lightbulb.Plugin("swear counter")

# Define swear constants
SWEARS: set[str] = set()
CLEAN_WORDS: set[str] = set()
SWEAR_ACHIEVEMENTS: dict[str, dict[str, str]] = {}  # individual swears
TOTAL_ACHIEVEMENTS: dict[str, str] = {}  # achievements for total swearing

SWEAR_COUNTER_DIR = f"{Bot.base_dir}/text/swear_counter"


@swear_counter.listener(hikari.StartedEvent)
async def create_word_lists(_: hikari.StartedEvent):
    """Creates swear constants."""

    # Swears and stuff
    global SWEARS, SWEAR_ACHIEVEMENTS, TOTAL_ACHIEVEMENTS
    async with aiofiles.open(f"{SWEAR_COUNTER_DIR}/swears.json", "r") as f:
        _swears = json.loads(await f.read())
        SWEAR_ACHIEVEMENTS = _swears["swears"]
        TOTAL_ACHIEVEMENTS = _swears["total"]
        SWEARS = set(SWEAR_ACHIEVEMENTS.keys())

    # Clean words
    global CLEAN_WORDS
    async with aiofiles.open(f"{SWEAR_COUNTER_DIR}/clean.txt", "r+") as f:
        async for line in f:
            CLEAN_WORDS.add(line.strip())


def count_swears(message: str) -> dict[str, int] | dict:
    """
    Counts the amount of swear words in a message.

    :param str message: The message to refer to.

    :return: A count of the swears used.
    :rtype dict[str, int] | dict:
    """
    swears_used = {}

    for word in message.split():
        for swear in SWEARS:
            if (swear in word) and (word not in CLEAN_WORDS):
                swears_used[str(swear)] = swears_used.get(str(swear), 0) + 1

    return swears_used


def get_achievements(
    keys: KeysView, result: dict[str, int]
) -> list[SwearAchievement] | list:
    """
    Gets the achievements obtained from a result after swearing.

    :param KeysView keys: A list of swears used in the message.
    :param dict[str, int] result: The swear count of the user after a swearing message.

    :return: A list of the achievements obtained.
    :rtype list[SwearAchievement]:
    """
    achievements_obtained = []

    for swear in keys:  # Can't use result.keys(), or else it counts extra swears
        total_amt = str(result.get(swear))
        if achievement_name := SWEAR_ACHIEVEMENTS[swear].get(total_amt):
            achievements_obtained.append(
                SwearAchievement(total_amt, achievement_name, swear)
            )

    # Add total swear achievements
    total_swears = str(sum(result.values()))
    if achievement_name := TOTAL_ACHIEVEMENTS.get(total_swears):
        achievements_obtained.append(
            SwearAchievement(total_swears, achievement_name, "total")
        )

    return achievements_obtained


async def parse_achievement(
    message: hikari.Message, achievement: SwearAchievement
) -> Message:
    """
    Parses an achievement and responds to a message.

    :param hikari.Message message: The message to refer.
    :param SwearAchievement achievement: The achievement, in [count | achievement name | swear] format.

    :return: The responded message.
    :rtype hikari.Message:
    """

    # Total swears
    if achievement.swear == "total":
        return await message.respond(
            hikari.Embed(
                title=achievement.name,
                description=f"Swear a total of **{achievement.count}** times.",
                color=0xFFBF00,
            )
        )

    return await message.respond(
        hikari.Embed(
            title=achievement.name,
            description=f"Say **{achievement.swear} {achievement.count}** times.",
            color=0xFFBF00,
        )
    )


@swear_counter.listener(hikari.GuildMessageCreateEvent)
async def on_message(message: hikari.GuildMessageCreateEvent) -> None:
    """Processes swears on every message."""

    # Check if human
    if message.is_bot:
        return

    # Check if any swears are in message
    if not message:
        return

    msg_swears = count_swears(message.content)
    if not msg_swears:
        return

    achievements = await update_swear_db(
        message.author_id, message.guild_id, msg_swears
    )  # update_swear_db returns the achievements obtained

    for achievement in achievements:
        await parse_achievement(message.message, achievement)


async def update_swear_db(
    user_id: int, guild_id: int, added_swears: dict[str, int]
) -> list[SwearAchievement] | list:
    """
    Updates the swear database. Returns any possible obtained achievements.

    :param int user_id: The ID of user to update.
    :param int guild_id: The ID of the guild to update.
    :param dict[str, int] added_swears: The swears to add to the user.

    :return: The list of achievements obtained
    :rtype: list[SwearAchievement] | list
    """

    bot = swear_counter.bot
    assert isinstance(bot, Bot)

    result = (
        await bot.db.fetchrow(
            """
            INSERT INTO swear_counter (user_id, guild_id, swears)
            VALUES ($1, $2, $3)
            ON CONFLICT (user_id, guild_id)
            DO UPDATE SET
                swears = (
                    SELECT swear_counter.swears || (
                        SELECT jsonb_object_agg(
                            key,
                            COALESCE(swear_counter.swears->>key, '0')::int + COALESCE(excluded.swears->>key)::int
                        )::jsonb
                        FROM jsonb_object_keys(excluded.swears) AS key
                    )
                )
            RETURNING swears;
        """,
            user_id,
            guild_id,
            added_swears,
        )
    )["swears"]

    return get_achievements(added_swears.keys(), result)


async def get_from_swear_db(
    guild_id: int,
    user_id: int = None,
) -> list[asyncpg.Record]:
    """
    Executes a query on the swear database.

    :param int user_id: The ID of user to update.
    :param int guild_id: The ID of the guild to update.

    :return: A list of records from the swear database.
    :rtype list[asyncpg.Record]:
    """

    bot = swear_counter.bot
    assert isinstance(bot, Bot)

    query = "SELECT * FROM swear_counter WHERE guild_id = $1 "
    if user_id:
        query += "AND user_id = $2"
        return await bot.db.fetch(query, guild_id, user_id)

    return await bot.db.fetch(query, guild_id)


async def delete_from_swear_db(
    guild_id: int, user_id: int | None = None
) -> asyncpg.Record:
    """
    Deletes an entry from the swear database.

    :param int guild_id: The ID of the guild to clear swears of.
    :param int | None user_id: The ID of the user to clear swears of.
    """
    bot = swear_counter.bot
    assert isinstance(bot, Bot)

    if not user_id:  # Delete guild swears
        query = "DELETE FROM swear_counter WHERE guild_id = $1"
        return await bot.db.execute(query, guild_id)

    # Delete user swears
    query = "DELETE FROM swear_counter WHERE guild_id = $1 AND user_id = $2"
    return await bot.db.execute(query, guild_id, user_id)


@swear_counter.command()
@lightbulb.command(name="swears", description="Command group for the swear counter.")
@lightbulb.implements(lightbulb.SlashCommandGroup)
async def swears():
    pass


@swears.child()
@lightbulb.option(
    name="user",
    description="User to get a swear count of.",
    type=hikari.Member,
    default=None,
)
@lightbulb.command(
    name="get",
    description="A list of everyone's swears in this server.",
    pass_options=True,
    auto_defer=True,
)
@lightbulb.implements(lightbulb.SlashSubCommand)
async def get_swears(ctx: lightbulb.SlashContext, user: hikari.Member | None = None):
    """COMMAND | Gets a count of a (or every) guild member's swears."""

    d = await get_from_swear_db(ctx.guild_id, user)  # Get data

    # No swears
    if not d:
        return await ctx.respond(
            hikari.Embed(
                title="No Swears Currently",
                description="What a nerd man, do y'all wash your mouths with soap?",
            )
        )

    # Parse user swears
    if user:
        user_swears = d[0].get("swears")
        msg = "".join(
            [f"{swear[0]}: **{swear[1]}** \n" for swear in user_swears.items()]
        )

        return await ctx.respond(
            hikari.Embed(title=f"{user.username}'s swears", description=msg)
        )

    # Parse guild swears
    msg = ""

    d.sort(key=lambda x: sum(v for v in x.get("swears").values()), reverse=True)
    for record in d:
        msg += f"<@{record.get('user_id')}>: **{sum(v for v in record.get('swears').values())}** \n"

    return await ctx.respond(
        hikari.Embed(
            title=f"Heaviest swearers in {ctx.get_guild().name}", description=msg
        )
    )


@swears.child()
@lightbulb.add_checks(lightbulb.has_guild_permissions(hikari.Permissions.MANAGE_GUILD))
@lightbulb.option(
    name="user",
    description="Resets a user's swear count.",
    type=hikari.Member,
    default=None,
)
@lightbulb.command(
    name="reset",
    description="Reset the server's swear count.",
    pass_options=True,
    auto_defer=True,
)
@lightbulb.implements(lightbulb.SlashSubCommand)
async def reset_user_swears(
    ctx: lightbulb.SlashContext, user: hikari.Member | None = None
):
    """COMMAND | Resets swears."""
    guild = ctx.get_guild()
    assert isinstance(guild, hikari.Guild)

    # Reset user swears
    if user:
        await delete_from_swear_db(guild.id, user.id)
        return await ctx.respond(
            hikari.Embed(
                title="Done!",
                description=f"Reset {user.mention}'s swears.",
                color=0x00FF00,
            )
        )

    # Reset guild swears
    await delete_from_swear_db(guild.id)
    return await ctx.respond(
        hikari.Embed(
            title="Done!",
            description=f"Reset **{guild.name}**'s swear count.",
            color=0x00FF00,
        )
    )


@swear_counter.listener(lightbulb.CommandErrorEvent)
async def on_error(event: lightbulb.CommandErrorEvent):
    """Error handler for swear counting."""

    if isinstance(event.exception, lightbulb.MissingRequiredPermission):
        await event.context.respond(
            hikari.Embed(
                title="nah",
                description="You don't have permissions to run this command.",
                color=0xF01000,
            )
        )


def load(bot: Bot):
    bot.add_plugin(swear_counter)


def unload(bot: Bot):
    bot.remove_plugin(swear_counter)
