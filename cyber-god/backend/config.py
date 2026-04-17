import os
from dotenv import load_dotenv

load_dotenv()

ZHIPU_API_KEY: str = os.environ["ZHIPU_API_KEY"]  # KeyError on startup if missing
GLM_MODEL: str = os.getenv("GLM_MODEL", "glm-4-flash")
ALLOWED_ORIGINS: list[str] = [
    o.strip() for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
]
