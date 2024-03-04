import hikari
import lightbulb

from src.models.bot import Bot


tag_manager = lightbulb.Plugin(name="tag manager")


async def create_tag(guild_id: int, key: str, value: str):
    """Adds a tag to the database."""
    bot = tag_manager.bot
    assert isinstance(bot, Bot)

    return await bot.db.execute(
        """
            INSERT INTO tags (guild_id, key, value)
            VALUES ($1, $2, $3)
        """,
        guild_id,
        key,
        value,
    )


async def delete_tag(guild_id: int, key: str):
    bot = tag_manager.bot
    assert isinstance(bot, Bot)

    return await bot.db.execute(
        """
            DELETE FROM tags WHERE guild_id = $1 AND key = $2
        """,
        guild_id,
        key,
    )


@tag_manager.command()
@lightbulb.command(name="tags", description="Base command for tag management.")
@lightbulb.implements(lightbulb.SlashCommandGroup)
async def tags():
    pass


def load(bot: Bot):
    bot.add_plugin(tag_manager)


def unload(bot: Bot):
    bot.remove_plugin(tag_manager)
