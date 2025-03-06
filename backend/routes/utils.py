import os

ENV = os.getenv("ENV", "dev")
if ENV == "PROD":
    BASE_URL = "https://gamergate.ai"
    FRONTEND_URL = "https://gamergate.ai"
else:
    BASE_URL = "http://localhost:8001"
    if ENV == "DEV":
        FRONTEND_URL = "http://localhost:5173"
    else:
        FRONTEND_URL = "http://localhost:8001"
