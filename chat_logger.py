import os
import datetime
import re
from pathlib import Path
import json


class ChatLogger:
    """
    Logger utility to save chat history in markdown format.
    Organizes logs by date and assigns sequential chat numbers.
    """

    def __init__(self, bot_username):
        """Initialize the logger with bot username and create history directory."""
        self.bot_username = bot_username
        self.history_dir = Path("history")
        self.history_dir.mkdir(exist_ok=True)

        # Current chat session info
        self.current_date = datetime.datetime.now().strftime("%Y-%m-%d")
        self.current_chat_number = self._get_next_chat_number()
        self.current_chat_file = self._create_chat_file()
        self.messages = []

        # Log the chat session start
        self._write_header()

    def _get_next_chat_number(self):
        """Determine the next chat number for today by checking existing files."""
        today_pattern = re.compile(f"{self.current_date}_chat_(\\d+)\\.md")
        max_num = 0

        for file in self.history_dir.glob(f"{self.current_date}_chat_*.md"):
            match = today_pattern.match(file.name)
            if match:
                num = int(match.group(1))
                max_num = max(max_num, num)

        return max_num + 1

    def _create_chat_file(self):
        """Create a new chat file with the appropriate naming pattern."""
        filename = f"{self.current_date}_chat_{self.current_chat_number}.md"
        return self.history_dir / filename

    def _write_header(self):
        """Write the header information to the chat file."""
        with open(self.current_chat_file, 'w', encoding='utf-8') as f:
            f.write(f"# Chat with @{self.bot_username}\n\n")
            f.write(f"Date: {self.current_date}\n")
            f.write(f"Chat Number: {self.current_chat_number}\n\n")
            f.write("---\n\n")

    def log_user_message(self, message):
        """Log a message sent by the user."""
        self.messages.append({"role": "user", "content": message})
        with open(self.current_chat_file, 'a', encoding='utf-8') as f:
            f.write(f"**You**: {message}\n\n")

    def log_bot_message(self, message):
        """Log a message received from the bot."""
        self.messages.append({"role": "assistant", "content": message})
        with open(self.current_chat_file, 'a', encoding='utf-8') as f:
            f.write(f"**{self.bot_username}**: {message}\n\n")

    def save_json(self):
        """Save the conversation in JSON format alongside the markdown file."""
        json_file = self.current_chat_file.with_suffix('.json')
        conversation = {
            "bot": self.bot_username,
            "date": self.current_date,
            "chat_number": self.current_chat_number,
            "messages": self.messages
        }

        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(conversation, f, indent=2, ensure_ascii=False)

    def get_filename(self):
        """Get the current chat filename."""
        return str(self.current_chat_file)

    def close(self):
        """Close the current chat session."""
        self.save_json()
        # Add a footer to indicate the chat has ended
        with open(self.current_chat_file, 'a', encoding='utf-8') as f:
            f.write("\n---\n\n")
            f.write(
                f"Chat ended at: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
