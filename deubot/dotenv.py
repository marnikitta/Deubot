import os
from pathlib import Path


def load_dotenv(path: Path = Path(".env")):
    if not path.is_file():
        pass

    with path.open("r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            key, _, value = line.partition("=")
            key, value = key.strip(), value.strip()

            if value.startswith('"') and value.endswith('"'):
                value = value[1:-1]
            elif value.startswith("'") and value.endswith("'"):
                value = value[1:-1]

            os.environ[key] = value
