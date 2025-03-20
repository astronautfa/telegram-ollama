import asyncio
from telethon import TelegramClient, events
import os
import sys
import time
import pyperclip
from telethon.tl.types import PeerUser
from config import API_ID, API_HASH, get_proxy_settings, SESSION_NAME, BOT_USERNAME
from chat_logger import ChatLogger

# ANSI color codes
GREEN = "\033[92m"
BLUE = "\033[94m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"
BG_BLACK = "\033[40m"
BG_GREEN = "\033[42m"
BG_BLUE = "\033[44m"

# Clear screen function


def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')


def print_header():
    """Print header with bot information"""
    terminal_width = os.get_terminal_size().columns
    header = f"{BOLD}{CYAN}Telegram CLI - Chatting with @{BOT_USERNAME}{RESET}"
    print("=" * terminal_width)
    print(header.center(terminal_width))
    print("=" * terminal_width)


def format_user_message(message):
    """Format user message for display"""
    lines = message.split('\n')
    formatted = f"\n{GREEN}{BOLD}You:{RESET}\n"
    for line in lines:
        formatted += f"  {GREEN}{line}{RESET}\n"
    return formatted


def format_bot_message(message):
    """Format bot message for display"""
    lines = message.split('\n')
    formatted = f"\n{BLUE}{BOLD}@{BOT_USERNAME}:{RESET}\n"
    for line in lines:
        formatted += f"  {BLUE}{line}{RESET}\n"
    return formatted


def format_system_message(message):
    """Format system message for display"""
    return f"{CYAN}{message}{RESET}\n"


def format_input_prompt(waiting=False):
    """Format the input prompt"""
    if waiting:
        return f"{YELLOW}[Waiting for response...]{RESET}\n"
    else:
        return f"{GREEN}>>> {RESET}"


def get_help_text():
    """Return the help text with keyboard shortcuts"""
    return (
        f"{BOLD}Keyboard Shortcuts:{RESET}\n"
        f"  • {BOLD}!q{RESET} - Quit the application\n"
        f"  • {BOLD}!copy{RESET} - Copy the last response to clipboard\n"
        f"  • {BOLD}!help{RESET} - Show this help menu\n"
        f"  • {BOLD}!clear{RESET} - Clear the screen\n"
        f"  • {BOLD}!new{RESET} - Start a new chat session\n"
    )


async def copy_to_clipboard(text):
    """Copy text to clipboard using pyperclip"""
    try:
        pyperclip.copy(text)
        return True
    except Exception as e:
        print(f"{RED}Failed to copy: {str(e)}{RESET}")
        return False


class TelegramChatCLI:
    def __init__(self):
        self.messages = []
        self.last_bot_message = ""
        self.waiting_for_response = asyncio.Event()
        self.waiting_for_response.set()  # Initially allow sending
        self.logger = None
        self.client = None
        self.bot = None

    async def initialize(self):
        """Initialize Telegram client and connect"""
        # Check API credentials
        if not API_ID or not API_HASH:
            print(f"{RED}Error: Telegram API credentials not found.{RESET}")
            print("Please set TELEGRAM_API_ID and TELEGRAM_API_HASH in your .env file.")
            return False

        # Check bot username
        if not BOT_USERNAME:
            print(f"{RED}Error: Bot username not found.{RESET}")
            print("Please set TELEGRAM_BOT_USERNAME in your .env file.")
            return False

        # Initialize chat logger
        self.logger = ChatLogger(BOT_USERNAME)
        print(format_system_message(
            f"Chat history will be saved to: {self.logger.get_filename()}"))

        # Create the client with proxy settings
        proxy = get_proxy_settings()
        self.client = TelegramClient(
            SESSION_NAME, API_ID, API_HASH, proxy=proxy)

        try:
            await self.client.start()

            # Get the bot entity at startup
            self.bot = await self.client.get_entity(BOT_USERNAME)
            print(format_system_message(
                f"Connected to Telegram and found bot: {BOT_USERNAME}"))

            # Set up message handler
            @self.client.on(events.NewMessage(from_users=self.bot.id))
            async def handle_new_message(event):
                """Handle incoming messages from the bot"""
                # Get the message text
                message_text = event.message.message

                # Log the bot's message
                self.logger.log_bot_message(message_text)

                # Add to local history
                self.messages.append({"text": message_text, "type": "bot"})
                self.last_bot_message = message_text

                # Print the formatted message
                print(format_bot_message(message_text))

                # Show input prompt
                print(format_input_prompt(waiting=False), end='')

                # Allow sending new messages
                self.waiting_for_response.set()

            return True

        except Exception as e:
            print(f"{RED}Error during startup: {e}{RESET}")
            return False

    async def start_new_chat(self):
        """Start a new chat session"""
        # Log the end of the current chat
        if self.logger:
            self.logger.close()

        # Create a new logger instance
        self.logger = ChatLogger(BOT_USERNAME)
        self.messages = []  # Reset local message history
        self.last_bot_message = ""

        # Send /newchat command to the bot
        try:
            await self.client.send_message(self.bot, "/newchat")
            print(format_system_message(
                "Sent /newchat command to bot. Starting a new chat session..."))
        except Exception as e:
            print(f"{RED}Error sending /newchat command: {e}{RESET}")

        print(format_system_message(
            f"Chat history will be saved to: {self.logger.get_filename()}"))

    async def send_message(self, message):
        """Send a message to the bot"""
        if not message.strip():
            return

        # Process special commands
        if message.strip().lower() == "!help":
            print(get_help_text())
            return

        if message.strip().lower() == "!copy":
            if self.last_bot_message:
                success = await copy_to_clipboard(self.last_bot_message)
                if success:
                    print(format_system_message(
                        "Last response copied to clipboard!"))
            else:
                print(format_system_message("No responses to copy yet."))
            return

        if message.strip().lower() == "!clear":
            clear_screen()
            print_header()
            return

        if message.strip().lower() == "!new" or message.strip().lower() == "/newchat":
            await self.start_new_chat()
            return

        # Log the user's message
        self.logger.log_user_message(message)

        # Add to local history
        self.messages.append({"text": message, "type": "user"})

        # Display in chat
        print(format_user_message(message))

        # Block sending new messages until we get a response
        self.waiting_for_response.clear()

        # Show waiting prompt
        print(format_input_prompt(waiting=True), end='')

        # Send message to the bot
        try:
            await self.client.send_message(self.bot, message)
        except Exception as e:
            print(f"{RED}Error sending message: {e}{RESET}")
            self.waiting_for_response.set()

    async def run(self):
        """Main chat loop"""
        print_header()
        print(format_system_message("Type your messages and press Enter to send."))
        print(format_system_message("Type !help to see all available commands."))

        while True:
            # Wait until we're allowed to send
            await self.waiting_for_response.wait()

            # Get user input
            try:
                message = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: input(format_input_prompt(waiting=False))
                )

                if message.strip().lower() == "!q":
                    break

                await self.send_message(message)

            except (KeyboardInterrupt, EOFError):
                print("\nExiting...")
                break

        # Close up
        if self.logger:
            self.logger.close()
        if self.client:
            await self.client.disconnect()
        print(format_system_message(
            f"Chat session ended. History saved to: {self.logger.get_filename()}"))


async def main():
    """Main application entry point"""
    clear_screen()

    cli = TelegramChatCLI()
    success = await cli.initialize()

    if success:
        await cli.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting due to keyboard interrupt...")
    except Exception as e:
        print(f"\n{RED}Unexpected error: {e}{RESET}")
