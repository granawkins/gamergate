import os

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, FileResponse

from routes.api import app as api_app
from db import db, initialize_admin_and_templates


async def startup_db_client():
    await db.connect()
    await initialize_admin_and_templates()


async def shutdown_db_client():
    await db.close()


app = FastAPI(
    on_startup=[startup_db_client],
    on_shutdown=[shutdown_db_client],
)

app.mount("/api", api_app)


@app.get("/{full_path:path}")
async def serve_index(request: Request, full_path: str):
    public_file_path = os.path.join("../frontend/dist", full_path)
    if os.path.exists(public_file_path) and os.path.isfile(public_file_path):
        return FileResponse(public_file_path)
    with open("../frontend/dist/index.html") as file:
        return HTMLResponse(content=file.read())
