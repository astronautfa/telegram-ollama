# Telegram Bots Ollama API

This project provides an Ollama-compatible API interface to Telegram bots, allowing you to use platforms like OpenWebUI with Telegram-based language models.

## Philosophy

Telegram Bots Ollama API bridges the gap between powerful AI models accessible via Telegram and your local workflow tools. We believe that:

1. **AI should be accessible everywhere**: By connecting Telegram bots to Ollama-compatible interfaces, we enable users to interact with advanced AI models through familiar tools.

2. **Your tools, your choice**: Whether you prefer a terminal, a web UI, or integration into development environments, you should be able to use AI assistants your way.

3. **Simplicity and flexibility**: The tool should be simple to set up but extensible enough to accommodate diverse workflows and use cases.

Currently, the project supports models like GrokAI, which is freely available to Telegram Premium users through the @GrokAI bot.

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

## Supported Models

Currently, we recommend using this tool with:

- **@GrokAI**: Available for free to Telegram Premium users
- Other Telegram-based AI bots (implementation may vary)

## Contributing

Contributions are welcome! Whether it's bug fixes, feature enhancements, or documentation improvements, please feel free to submit issues or pull requests.

## Roadmap & TODOs

### API Integration

- [ ] Test Telegram API with Ollama
  - [ ] Verify compatibility with OpenWebUI
  - [ ] Test with other Ollama-compatible clients
  - [ ] Implement proper error handling for API responses
  - [ ] Add rate limiting and retry logic

### File Management

- [ ] Add file upload functionality to terminal interface
  - [ ] Support basic document formats (PDF, DOCX, TXT)
  - [ ] Implement image uploads
  - [ ] Add progress indicators for large files
- [ ] Implement file tree analysis for coding projects
  - [ ] Create keyboard-based navigation for directory structures
  - [ ] Add context selection capabilities
  - [ ] Implement syntax highlighting for code files

### Agent Capabilities

- [ ] Transform into a workflow agent
  - [ ] Enable task automation based on chat interactions
  - [ ] Add scheduled operations
  - [ ] Create hooks for external tools and scripts
  - [ ] Implement context awareness between sessions

### Interface Improvements

- [ ] Enhance command line interface
  - [ ] Add theme customization
  - [ ] Implement split-screen views
  - [ ] Add conversation search functionality
  - [ ] Create a TUI (Text User Interface) with panels
  - [ ] Add keyboard shortcuts for common operations

### Multi-Model Support

- [ ] Add support for multiple Telegram bots
  - [ ] Implement model switching
  - [ ] Create model comparison features
  - [ ] Add context sharing between models

## License

MIT
