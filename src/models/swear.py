import attrs


@attrs.define
class SwearAchievement:
    """Represents an achievement obtained from swearing a specific number of times."""

    """The amount of times the swear was used (in string format)."""
    count: str

    """The name of the achievement."""
    name: str

    """The swear used."""
    swear: str
