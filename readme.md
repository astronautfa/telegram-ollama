# Telegram Bots Ollama API

This project provides an Ollama-compatible API interface to Telegram bots, allowing you to use platforms like OpenWebUI and LMStudio with Telegram-based language models.

## Philosophy

Telegram Bots Ollama API bridges the gap between powerful AI models accessible via Telegram and your local workflow tools. We believe that:

1. **AI should be accessible everywhere**: By connecting Telegram bots to Ollama-compatible interfaces, we enable users to interact with advanced AI models through familiar tools.

2. **Your tools, your choice**: Whether you prefer a terminal, a web UI, or integration into development environments, you should be able to use AI assistants your way.

3. **Simplicity and flexibility**: The tool should be simple to set up but extensible enough to accommodate diverse workflows and use cases.

Currently, the project supports models like GrokAI, which is freely available to Telegram Premium users through the @GrokAI bot.

## Features

- Terminal interface for interacting with Telegram
- Ollama-compatible API for integration with OpenWebUI, LMStudio and other clients
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

## Using with OpenWebUI or LMStudio

1. In OpenWebUI or LMStudio, add a new Ollama server with the URL pointing to your API server (e.g., <http://localhost:11434>)
2. You should see "telegram" listed as an available model
3. Start chatting through the interface

## API Reference

The API is compatible with Ollama's API format and supports the following endpoints:

### Model Management

#### List Models

```
GET /api/tags
```

Lists all available models (in this case, the Telegram bot as a model named "telegram").

**Response Example:**

```json
{
  "models": [
    {
      "name": "telegram",
      "modified_at": "2025-03-20T12:00:00Z",
      "size": 0,
      "digest": "telegram-bot",
      "details": {
        "format": "telegram",
        "family": "telegram",
        "parameter_size": "Unknown",
        "quantization_level": "None"
      }
    }
  ]
}
```

#### List Running Models

```
GET /api/ps
```

Lists models currently loaded in memory.

**Response Example:**

```json
{
  "models": [
    {
      "name": "telegram",
      "model": "telegram",
      "size": 0,
      "digest": "telegram-bot",
      "details": {
        "format": "telegram",
        "family": "telegram",
        "parameter_size": "Unknown",
        "quantization_level": "None"
      },
      "expires_at": "2025-03-20T12:05:00Z"
    }
  ]
}
```

#### Get API Version

```
GET /api/version
```

Returns the version of the API.

**Response Example:**

```json
{
  "version": "1.0.0"
}
```

### Text Generation

#### Generate Completion

```
POST /api/generate
```

Generate a response for a given prompt.

**Request Parameters:**

- `model` (required): The model name (use "telegram")
- `prompt` (required): The prompt to generate a response for
- `system` (optional): System message to prime the model
- `options` (optional): Additional parameters like temperature, etc.
- `keep_alive` (optional): How long to keep the model loaded

**Example Request:**

```json
{
  "model": "telegram",
  "prompt": "What is the capital of France?",
  "system": "You are a helpful assistant.",
  "options": {
    "temperature": 0.7
  }
}
```

**Example Response:**

```json
{
  "model": "telegram",
  "created_at": "2025-03-20T12:00:00Z",
  "response": "The capital of France is Paris.",
  "done": true,
  "context": [1, 2, 3],
  "total_duration": 1200000000,
  "load_duration": 0,
  "prompt_eval_count": 25,
  "prompt_eval_duration": 200000000,
  "eval_count": 20,
  "eval_duration": 1000000000
}
```

#### Generate Chat Completion

```
POST /api/chat
```

Generate the next message in a chat conversation.

**Request Parameters:**

- `model` (required): The model name (use "telegram")
- `messages` (required): Array of message objects with `role` and `content`
- `options` (optional): Additional parameters like temperature, etc.
- `keep_alive` (optional): How long to keep the model loaded

**Example Request:**

```json
{
  "model": "telegram",
  "messages": [
    {
      "role": "system",
      "content": "You are a helpful assistant."
    },
    {
      "role": "user",
      "content": "What is the capital of France?"
    }
  ],
  "options": {
    "temperature": 0.7
  }
}
```

**Example Response:**

```json
{
  "model": "telegram",
  "created_at": "2025-03-20T12:00:00Z",
  "message": {
    "role": "assistant",
    "content": "The capital of France is Paris."
  },
  "done": true,
  "total_duration": 1200000000,
  "load_duration": 0,
  "prompt_eval_count": 25,
  "prompt_eval_duration": 200000000,
  "eval_count": 20,
  "eval_duration": 1000000000
}
```

### Embeddings

#### Generate Embeddings

```
POST /api/embed
```

Generate embeddings for a text or list of texts.

**Request Parameters:**

- `model` (required): The model name
- `input` (required): Text or list of texts to generate embeddings for

**Example Request:**

```json
{
  "model": "telegram",
  "input": "What is the capital of France?"
}
```

**Example Response:**

```json
{
  "model": "telegram",
  "embeddings": [[0.1, 0.2, -0.3, ...]],
  "total_duration": 10000000,
  "load_duration": 1000000,
  "prompt_eval_count": 5
}
```

### History Management

#### List Chat History

```
GET /api/history
```

Get a list of all chat history files.

**Example Response:**

```json
{
  "history": [
    {
      "date": "2025-03-20",
      "chat_number": "1",
      "filename": "2025-03-20_chat_1.md",
      "path": "history/2025-03-20_chat_1.md"
    }
  ]
}
```

#### Get Chat History

```
GET /api/history/{date}/{chat_number}
```

Get the content of a specific chat history file.

**Example Response:**

```json
{
  "filename": "2025-03-20_chat_1.md",
  "content": "# Chat with @GrokAI\n\nDate: 2025-03-20\nChat Number: 1\n\n---\n\n**You**: What is the capital of France?\n\n**GrokAI**: The capital of France is Paris.\n\n",
  "messages": [
    {
      "role": "user",
      "content": "What is the capital of France?"
    },
    {
      "role": "assistant",
      "content": "The capital of France is Paris."
    }
  ]
}
```

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
- **Missing Responses**: Check the telegram_api.log file for details on any errors.

## Supported Models

Currently, we recommend using this tool with:

- **@GrokAI**: Available for free to Telegram Premium users
- Other Telegram-based AI bots (implementation may vary)

## Contributing

Contributions are welcome! Whether it's bug fixes, feature enhancements, or documentation improvements, please feel free to submit issues or pull requests.

## Roadmap & TODOs

### API Improvements

- [ ] Add support for streaming responses (if Telegram ever supports it)
- [ ] Implement proper embeddings via a local model
- [ ] Add support for multiple Telegram bots as different "models"
- [ ] Add support for image processing with multimodal bots

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

## License

MIT
