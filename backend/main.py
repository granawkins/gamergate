from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
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


from fastapi.responses import HTMLResponse
import re

@app.get("/games/{game_name}/play")
async def serve_game(game_name: str):
    """Serve the HTML file for a specific game with added resize handling."""
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
    
    # Add resize event listener to update canvas size
    # This injects a script that handles window resize events and updates the canvas size
    resize_script = """
    <script>
    // Handle window resize events
    function handleResize() {
        // Update window dimensions
        window.innerWidth = window.parent.innerWidth;
        window.innerHeight = window.parent.innerHeight;
        
        // Find all canvas elements
        const canvases = document.querySelectorAll('canvas');
        canvases.forEach(canvas => {
            // Update canvas size to match parent container
            const container = canvas.parentElement;
            if (container) {
                canvas.width = container.clientWidth || window.innerWidth;
                canvas.height = container.clientHeight || window.innerHeight;
            }
        });
        
        // Handle Three.js specific resize
        if (window.renderer && window.camera) {
            console.log('Resizing Three.js renderer');
            window.renderer.setSize(window.innerWidth, window.innerHeight);
            if (window.camera.aspect) {
                window.camera.aspect = window.innerWidth / window.innerHeight;
                window.camera.updateProjectionMatrix();
            }
        }
        
        // Dispatch a custom resize event for game engines to handle
        window.dispatchEvent(new Event('game-resize'));
    }
    
    // Override the original renderer setup to capture the renderer instance
    if (typeof THREE !== 'undefined') {
        const originalWebGLRenderer = THREE.WebGLRenderer;
        THREE.WebGLRenderer = function(...args) {
            const renderer = new originalWebGLRenderer(...args);
            window.renderer = renderer;
            return renderer;
        };
        
        // Also try to capture the camera
        const originalPerspectiveCamera = THREE.PerspectiveCamera;
        THREE.PerspectiveCamera = function(...args) {
            const camera = new originalPerspectiveCamera(...args);
            window.camera = camera;
            return camera;
        };
    }
    
    // Add window resize listener
    window.addEventListener('resize', handleResize);
    
    // Handle messages from parent frame
    window.addEventListener('message', function(event) {
        if (event.data === 'resize') {
            console.log('Received resize message from parent');
            handleResize();
        }
    });
    
    // Initial resize after load
    window.addEventListener('load', function() {
        console.log('Game loaded, initializing resize');
        // Give a bit of time for Three.js to initialize
        setTimeout(handleResize, 200);
    });
    </script>
    """
    
    # Insert the resize script before the closing </body> tag
    if "</body>" in html_content:
        html_content = html_content.replace("</body>", f"{resize_script}</body>")
    else:
        html_content += resize_script
    
    # Add viewport meta tag if not present
    if "<meta name=\"viewport\"" not in html_content and "<head>" in html_content:
        viewport_meta = '<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">'
        html_content = html_content.replace("<head>", f"<head>\n    {viewport_meta}")
    
    # Add CSS to ensure full-size content without scrollbars
    style_tag = """
    <style>
    html, body {
        margin: 0;
        padding: 0;
        width: 100%;
        height: 100%;
        overflow: hidden;
    }
    #game, canvas {
        width: 100% !important;
        height: 100% !important;
        display: block;
    }
    </style>
    """
    
    if "<head>" in html_content:
        html_content = html_content.replace("<head>", f"<head>\n    {style_tag}")
    else:
        html_content = f"{style_tag}\n{html_content}"
    
    return HTMLResponse(content=html_content)
