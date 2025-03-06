import os

from dotenv import load_dotenv

load_dotenv()

ENV = os.getenv("ENV", "DEV")
if ENV == "PROD":
    BASE_URL = "https://gamergate.ai"
    FRONTEND_URL = "https://gamergate.ai"
else:
    BASE_URL = "http://localhost:8001"
    if ENV == "DEV":
        FRONTEND_URL = "http://localhost:5173"
    else:
        FRONTEND_URL = "http://localhost:8001"
