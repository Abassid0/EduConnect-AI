import random
from datetime import datetime


def generate_registration_id() -> str:
    year = datetime.now().year
    seq = random.randint(10000, 99999)
    return f"EDP-{year}-{seq}"
