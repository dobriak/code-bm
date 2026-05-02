import random

from raidio.core.names import ADJECTIVES, SCIENTISTS


def generate_name() -> str:
    adj = random.choice(ADJECTIVES)
    scientist = random.choice(SCIENTISTS)
    return f"{adj}_{scientist}"

