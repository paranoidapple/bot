import hikari
import lightbulb

import asyncpg
import aiofiles
import json

from src.models.bot import Bot

swear_counter = lightbulb.Plugin("swear counter")

# Define swear constants
SWEARS: set[str] = set()
CLEAN_WORDS: set[str] = set()
SWEAR_ACHIEVEMENTS: dict[str, dict[str, str]] = {}  # achievements for each individual sewar
TOTAL_ACHIEVEMENTS: dict[str, str] = {}  # achievements for total swearing

SWEAR_COUNTER_DIR = f"{Bot.base_dir}/text/swear_counter"


@swear_counter.listener(hikari.StartedEvent)
async def create_word_lists(_: hikari.StartedEvent):
    """Creates swear constants."""

    # Swears and stuff
    global SWEARS, SWEAR_ACHIEVEMENTS, TOTAL_ACHIEVEMENTS
    async with aiofiles.open(f"{SWEAR_COUNTER_DIR}/swears.json", "r") as f:
        swears = json.loads(await f.read())
        SWEAR_ACHIEVEMENTS = swears["swears"]
        TOTAL_ACHIEVEMENTS = swears["total"]
        SWEARS = set(SWEAR_ACHIEVEMENTS.keys())

    # Clean words
    global CLEAN_WORDS
    async with aiofiles.open(f"{SWEAR_COUNTER_DIR}/clean.txt", "r+") as f:
        async for line in f:
            CLEAN_WORDS.add(line.strip())


def count_swears(message: str | None) -> dict[str, int]:
    """Counts the amount of swear words in a message."""
    swears_used = {}

    for word in str(message).split():
        for swear in SWEARS:
            if (swear in word) and (word not in CLEAN_WORDS):
                swears_used[str(swear)] = swears_used.get(str(swear), 0) + 1

    return swears_used


@swear_counter.listener(hikari.GuildMessageCreateEvent)
async def on_message(event: hikari.GuildMessageCreateEvent):
    """Processes swears on every message."""
    if event.is_human:
        msg = event.message

        msg_swears = count_swears(msg.content)
        if msg_swears:
            achievements = await update_swear_db(
                event.author_id, event.guild_id, msg_swears
            )  # update_swear_db returns the achievements obtained

            for achievement in achievements:
                if achievement[2] == "total":
                    await event.message.respond(
                        hikari.Embed(
                            title=achievement[1],
                            description=f"Swear a total of **{achievement[0]}** times.",
                            color=0xFFBF00,
                        )
                    )
                else:
                    await event.message.respond(
                        hikari.Embed(
                            title=achievement[1],
                            description=f"Say **{achievement[2]} {achievement[0]}** times.",
                            color=0xFFBF00,
                        )
                    )


async def update_swear_db(
    user_id: int, guild_id: int, added_swears: dict[str, int]
) -> list[tuple[str, str, str]] | list[None]:
    """Updates the swear database. Returns any possible obtained achievements."""
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
    achievements_obtained = []

    # Add individual swear achievements
    for swear in added_swears:
        total_amt = str(result.get(swear))  # total times the swear was used
        if achievement_name := SWEAR_ACHIEVEMENTS[swear].get(total_amt):
            achievements_obtained.append((total_amt, achievement_name, swear))

    # Add total swear achievements
    total_swears = str(sum(result.values()))
    if achievement_name := TOTAL_ACHIEVEMENTS.get(total_swears):
        achievements_obtained.append((total_swears, achievement_name, "total"))

    return achievements_obtained


async def select_from_swear_db(
    guild_id: int, user: hikari.Member = None
) -> list[asyncpg.Record]:
    """Executes a query on the swear database."""
    bot = swear_counter.bot
    assert isinstance(bot, Bot)

    query = "SELECT * FROM swear_counter WHERE guild_id = $1 "
    if user:
        user_id = user.id
        query += "AND user_id = $2"
        return await bot.db.fetch(query, guild_id, user_id)

    return await bot.db.fetch(query, guild_id)


async def delete_from_swear_db(guild_id: int, user_id: int = None) -> None:
    """Deletes an entry from the swear database."""
    bot = swear_counter.bot
    assert isinstance(bot, Bot)

    if not user_id:  # delete guild
        query = "DELETE FROM swear_counter WHERE guild_id = $1"
        return await bot.db.execute(query, guild_id)

    else:
        query = "DELETE FROM swear_counter WHERE guild_id = $1 AND user_id = $2"
        await bot.db.execute(query, guild_id, user_id)


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
async def get_swears(ctx: lightbulb.SlashContext, user: hikari.Member = None):
    """COMMAND | Gets a count of a (or every) guild member's swears."""

    d = await select_from_swear_db(ctx.guild_id, user)  # Get data

    # No swears
    if not d:
        return await ctx.respond(
            hikari.Embed(
                title="No Swears Currently",
                description="What a nerd man, do y'all wash your mouths with soap?",
            )
        )

    # Parse user swears
    msg = ""
    if user:
        swears = d[0].get("swears")
        for swear in swears.items():
            msg += f"{swear[0]}: **{swear[1]}** \n"

        return await ctx.respond(
            hikari.Embed(title=f"{user.username}'s swears", description=msg)
        )

    # Parse guild swears
    else:
        d.sort(key=lambda x: sum(v for v in x.get("swears").values()), reverse=True)
        for record in d:
            msg += f"<@{record.get('user_id')}>: **{sum(v for v in record.get('swears').values())}** \n"

        return await ctx.respond(
            hikari.Embed(
                title=f"Heaviest swearers in {ctx.get_guild().name}", description=msg
            )
        )


@swears.child()
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
async def reset_user_swears(ctx: lightbulb.SlashContext, user: hikari.Member | None):
    """COMMAND | Resets swears."""

    if user:
        # Reset user swears
        await delete_from_swear_db(ctx.get_guild().id, user.id)
        return await ctx.respond(
            hikari.Embed(
                title="Done!",
                description=f"Reset {user.mention}'s swears.",
                color=0x00FF00,
            )
        )

    else:  # Reset guild swears
        await delete_from_swear_db(ctx.get_guild().id)
        return await ctx.respond(
            hikari.Embed(
                title="Done!",
                description=f"Reset **{ctx.get_guild().name}**'s swear count.",
                color=0x00FF00,
            )
        )


def load(bot: Bot):
    bot.add_plugin(swear_counter)


def unload(bot: Bot):
    bot.remove_plugin(swear_counter)
