# Telegram LLM API (Ollama Compatible)

This project provides an Ollama-compatible API interface to Telegram bots, allowing you to use platforms like OpenWebUI with Telegram-based language models.

## Features

- Terminal interface for interacting with Telegram
- Ollama-compatible API for integration with OpenWebUI and other clients
- SSH tunnel/proxy support for secure connections
- Environment-based configuration
- Comprehensive chat logging with markdown and JSON formats
- Chat history organized by date and sequential chat numbers

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Copy the example environment file and fill in your details:

```bash
cp .env.example .env
```

Edit the `.env` file with your Telegram API credentials and other settings:

- `TELEGRAM_API_ID` and `TELEGRAM_API_HASH`: Get these from <https://my.telegram.org/>
- `TELEGRAM_BOT_USERNAME`: The username of the Telegram bot you want to interact with
- `PROXY_ENABLED`: Set to `true` to use SSH tunnel/proxy
- Other proxy and API server settings

### 3. Set Up SSH Tunnel (Optional)

If you want to route traffic through an SSH tunnel:

```bash
ssh -D 9000 -f -C -q -N -p 22 user@your-ssh-server.com
```

Make sure `PROXY_ENABLED=true` in your `.env` file.

### 4. Run the Application

#### Terminal Interface

```bash
python telegram-cli.py
```

#### API Server

```bash
python telegram-api.py
```

The API server will run on the host and port specified in your `.env` file (default: `0.0.0.0:11434`).

#### View Chat History

To view chat history from the command line:

```bash
# List all chat histories
python view_history.py list

# List chat histories for a specific date
python view_history.py list -d 2025-03-20

# View a specific chat history
python view_history.py view 2025-03-20 1
```

All chat histories are stored in the `history/` directory in both markdown (`.md`) and JSON (`.json`) formats.

## Using with OpenWebUI

1. In OpenWebUI, add a new Ollama server with the URL pointing to your API server (e.g., <http://localhost:11434>)
2. You should see "telegram" listed as an available model
3. Start chatting through the interface

## Advanced Configuration

### SSH Tunnel Persistence

Add to your `~/.ssh/config`:

```
Host your-ssh-server.com
    ServerAliveInterval 60
    ServerAliveCountMax 3
```

### Running as a Service

Create a systemd service file for automatic startup and restarts.

## Troubleshooting

- **Connection Issues**: Ensure your API credentials are correct and that your SSH tunnel is running (if enabled).
- **Authentication Problems**: If you're using two-factor authentication with Telegram, you may need to handle that in the code.
- **Missing Responses**: The current implementation uses a simplified placeholder for responses. You'll need to implement proper event handling.

## Contributing

Feel free to submit issues or pull requests!

## License

MIT
