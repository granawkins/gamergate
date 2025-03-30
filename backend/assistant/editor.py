import os
import subprocess
from pathlib import Path

from db import GAMES_PATH
from assistant.errors import BadResponseError


class Editor:
    def __init__(self, game_id: str):
        self.cwd = GAMES_PATH / game_id
        self.edit_history: dict[str, list[str]] = {}

    def get_file_content(self, path: str) -> str:
        if not Path(self.cwd / path).exists():
            raise FileNotFoundError(f"File {path} does not exist")
        return Path(self.cwd / path).read_text()

    def write_file_content(self, path: str, content: str):
        Path(self.cwd / path).write_text(content)

    def edit_file_content(self, path: str, content: str):
        current_content = self.get_file_content(path)
        if path not in self.edit_history:
            self.edit_history[path] = []
        self.edit_history[path].append(current_content)
        self.write_file_content(path, content)

    def handle_editor_tool(self, input_params: dict) -> str:
        command = input_params.get("command", "")
        path = input_params.get("path", "")

        # Claude usually adds a leading slash to the path, so we remove it
        if path.startswith("/"):
            path = path[1:]

        if command == "view":
            view_range = input_params.get("view_range", [1, -1])
            is_dir = os.path.isdir(path)
            if is_dir:
                try:
                    result = subprocess.run(
                        ["git", "ls-files", str(path)],
                        capture_output=True,
                        text=True,
                        cwd=self.cwd,
                    )
                    return result.stdout.strip()
                except Exception:
                    return "\n".join(os.listdir(self.cwd / path))
            content = self.get_file_content(path)
            start, end = view_range
            output = ""
            for i, line in enumerate(content.split("\n")):
                line_num = i + 1
                if line_num >= start and (line_num <= end or end == -1):
                    output += f"{line_num}: {line}\n"
            return output

        elif command == "str_replace":
            old_str = input_params.get("old_str", "")
            new_str = input_params.get("new_str", "")
            content = self.get_file_content(path)
            count = content.count(old_str)
            if count == 0:
                raise Exception(
                    "No match found for replacement. Please check your text and try again."
                )
            if count > 1:
                raise Exception(
                    f"Found {count} matches for replacement text. Please provide more context to make a unique match."
                )
            self.edit_file_content(path, content.replace(old_str, new_str))
            return "Successfully replaced text at exactly one location."

        elif command == "create":
            file_text = input_params.get("file_text", "")
            if Path(self.cwd / path).exists():
                raise Exception(f"File {path} already exists")
            self.write_file_content(self.cwd / path, file_text)
            return f"Successfully created file {path}"

        elif command == "insert":
            insert_line: int = input_params.get("insert_line", 0)
            new_str: str = input_params.get("new_str", "")
            content = self.get_file_content(path)
            lines = content.split("\n")
            lines.insert(insert_line, new_str)
            self.edit_file_content(path, "\n".join(lines))
            return f"Successfully inserted text at line {insert_line}"

        elif command == "undo_edit":
            path = input_params.get("path", "")
            previous_content = self.edit_history[path].pop()
            self.write_file_content(path, previous_content)
            return f"Successfully undone edit to file {path}"

        else:
            raise BadResponseError(f"Unknown command: {command}")

    async def commit_changes(self, commit_message: str) -> str | None:
        # Check if there are changes to commit
        status_result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=self.cwd,
            capture_output=True,
            text=True,
        )

        # If there are no changes, return None
        if not status_result.stdout.strip():
            return None

        # Apply to codebase
        subprocess.run(["git", "add", "index.html"], cwd=self.cwd)
        # First make the commit
        subprocess.run(
            [
                "git",
                "commit",
                "-m",
                commit_message,
            ],
            cwd=self.cwd,
        )
        # Then get the commit hash
        commit_result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=self.cwd,
            capture_output=True,
        )
        commit_sha = commit_result.stdout.strip().decode("utf-8")
        return commit_sha
