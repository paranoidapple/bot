import attrs


@attrs.define
class SwearAchievement:
    """Represents an achievement obtained from swearing a specific number of times."""

    count: str
    """The amount of times the swear was used (in string format)."""

    name: str
    """The name of the achievement."""

    swear: str
    """The swear used."""
