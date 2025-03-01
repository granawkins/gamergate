from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
import re
import mimetypes
from pathlib import Path

from db import db, GAMES_PATH
from user import app as user_app

app = FastAPI(root_path="/api")

app.mount("/user", user_app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Default Vite dev server port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/games")
async def get_games():
    _db = await db.get()
    return list(_db["games"].values())


@app.get("/games/{game_name}/assets/{asset_path:path}")
async def serve_game_asset(game_name: str, asset_path: str):
    """Serve game assets like JavaScript, CSS, images, etc."""
    game_dir = GAMES_PATH / game_name
    
    # Ensure the game directory exists
    if not game_dir.exists() or not game_dir.is_dir():
        raise HTTPException(status_code=404, detail=f"Game '{game_name}' not found")
    
    # Construct the asset path
    asset_file = game_dir / asset_path
    
    # Check if the asset exists
    if not asset_file.exists() or asset_file.is_dir():
        raise HTTPException(status_code=404, detail=f"Asset not found: {asset_path}")
    
    # Determine content type based on file extension
    content_type, _ = mimetypes.guess_type(asset_file)
    
    # Return the file with appropriate headers
    return FileResponse(
        asset_file,
        media_type=content_type,
        headers={"Cache-Control": "public, max-age=3600"}  # Cache for 1 hour
    )


@app.get("/games/{game_name}/play")
async def serve_game(game_name: str):
    """Serve the HTML file for a specific game with path rewriting."""
    game_dir = GAMES_PATH / game_name

    # First check if there's a file named after the game
    game_file = game_dir / f"{game_name}.html"
    if not game_file.exists():
        # If not, look for any HTML file in the directory
        html_files = list(game_dir.glob("*.html"))
        if html_files:
            game_file = html_files[0]
        else:
            # If no HTML file is found, return 404
            raise HTTPException(status_code=404, detail=f"Game '{game_name}' not found")

    # Read the HTML content
    with open(game_file, "r") as f:
        html_content = f.read()
    
    # Rewrite asset paths in HTML
    
    # 1. Rewrite absolute paths that don't start with http(s):// or //
    # This handles paths like src="/js/script.js" or href="/css/style.css"
    html_content = re.sub(
        r'(src|href)="(/[^"]*)"',
        f'\\1="/api/games/{game_name}/assets\\2"',
        html_content
    )
    
    # 2. Rewrite relative paths that don't include a protocol
    # This handles paths like src="js/script.js" or href="css/style.css"
    html_content = re.sub(
        r'(src|href)="(?!http|https|//|data:|#|/)([^"]*)"',
        f'\\1="/api/games/{game_name}/assets/\\2"',
        html_content
    )
    
    # 3. Rewrite any fetch/XMLHttpRequest URLs in inline scripts
    # This is more complex and might need refinement based on actual usage
    html_content = re.sub(
        r'(fetch\([\'"])(?!http|https|//|data:|#|/)([^\'"]*)[\'"]',
        f'\\1/api/games/{game_name}/assets/\\2"',
        html_content
    )
    
    # 4. Add a base path for dynamic imports in JavaScript
    base_path_script = f"""
    <script>
    // Add a global variable for the game's asset base path
    window.GAME_ASSET_BASE_PATH = "/api/games/{game_name}/assets/";
    
    // Override fetch to handle relative URLs
    const originalFetch = window.fetch;
    window.fetch = function(url, options) {{
        if (typeof url === 'string' && !url.match(/^(http|https|\/\/|data:|#|\/api)/)) {{
            url = window.GAME_ASSET_BASE_PATH + url;
        }}
        return originalFetch(url, options);
    }};
    </script>
    """
    
    # Insert the base path script before the first script tag or at the end of head
    if "<script" in html_content:
        html_content = html_content.replace("<script", f"{base_path_script}<script", 1)
    elif "</head>" in html_content:
        html_content = html_content.replace("</head>", f"{base_path_script}</head>", 1)
    else:
        # If no script tag or head tag, add it at the beginning of the body
        html_content = html_content.replace("<body", f"<body>{base_path_script}", 1)
    
    return HTMLResponse(content=html_content)
