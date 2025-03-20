from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import asyncio
import json
import uuid
from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError

# Import configuration
from config import (
    API_ID, API_HASH, BOT_USERNAME, get_proxy_settings,
    SESSION_NAME, API_HOST, API_PORT
)
from chat_logger import ChatLogger

# Initialize FastAPI
app = FastAPI(title="Telegram LLM API")

# Add CORS middleware to allow requests from OpenWebUI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create a dictionary to store active conversations and their loggers
active_chats = {}

# Dictionary to store chat loggers for each conversation
chat_loggers = {}

# Request models that match Ollama's API


class GenerateRequest(BaseModel):
    model: str
    prompt: str
    system: Optional[str] = None
    template: Optional[str] = None
    context: Optional[List[int]] = None
    options: Optional[Dict[str, Any]] = None
    stream: Optional[bool] = False


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    stream: Optional[bool] = False
    options: Optional[Dict[str, Any]] = None


class ModelInfo(BaseModel):
    name: str
    modified_at: str
    size: int
    digest: str
    details: Dict[str, Any]

# Function to get or create client


async def get_client():
    if not hasattr(app, "telegram_client") or app.telegram_client is None:
        proxy = get_proxy_settings()
        app.telegram_client = TelegramClient(
            SESSION_NAME, API_ID, API_HASH, proxy=proxy)
        await app.telegram_client.start()
    return app.telegram_client

# Initialize the client on startup


@app.on_event("startup")
async def startup_event():
    if not API_ID or not API_HASH:
        print("Error: Telegram API credentials not found in environment variables.")
        print("Please set TELEGRAM_API_ID and TELEGRAM_API_HASH in your .env file.")
        import sys
        sys.exit(1)

    if not BOT_USERNAME:
        print("Warning: TELEGRAM_BOT_USERNAME not set. This is required for the API to work properly.")

    app.telegram_client = None
    await get_client()
    print(f"Telegram API server started on {API_HOST}:{API_PORT}")
    print(f"Using proxy: {get_proxy_settings() is not None}")

# Shutdown the client on app shutdown


@app.on_event("shutdown")
async def shutdown_event():
    # Close all chat loggers
    for conversation_id, logger in chat_loggers.items():
        logger.close()

    if hasattr(app, "telegram_client") and app.telegram_client is not None:
        await app.telegram_client.disconnect()

# Route to list available models (mimicking Ollama)


@app.get("/api/tags")
async def list_models():
    # For compatibility with OpenWebUI, we'll return a hardcoded model that represents our Telegram bot
    return {
        "models": [
            {
                "name": "telegram",
                "modified_at": "2025-03-20T12:00:00Z",
                "size": 0,
                "digest": "telegram",
                "details": {
                    "parameter_size": "Unknown",
                    "quantization_level": "None"
                }
            }
        ]
    }

# Helper function to send message and get response


async def send_and_get_response(prompt, conversation_id=None):
    client = await get_client()

    if not BOT_USERNAME:
        raise HTTPException(
            status_code=500, detail="TELEGRAM_BOT_USERNAME not configured")

    try:
        # Get the bot entity
        bot = await client.get_entity(BOT_USERNAME)

        # Generate a unique ID for this conversation if not provided
        if not conversation_id:
            conversation_id = str(uuid.uuid4())

            # Create a new logger for this conversation
            logger = ChatLogger(BOT_USERNAME)
            chat_loggers[conversation_id] = logger
        else:
            # Get existing logger or create a new one
            logger = chat_loggers.get(conversation_id)
            if not logger:
                logger = ChatLogger(BOT_USERNAME)
                chat_loggers[conversation_id] = logger

        # Store the conversation in active chats
        active_chats[conversation_id] = {
            "bot": bot,
            "messages": []
        }

        # Log the user message
        logger.log_user_message(prompt)

        # Send the message
        await client.send_message(bot, prompt)

        # Wait for response using the proper events mechanism
        response = await wait_for_bot_response(client, bot, conversation_id)

        # Log the bot response
        logger.log_bot_message(response)

        # Save the conversation
        logger.save_json()

        return {
            "model": "telegram",
            "created_at": datetime.datetime.now().isoformat(),
            "response": response,
            "done": True,
            "context": [],
            "conversation_id": conversation_id,
            "log_file": logger.get_filename(),
            "total_duration": 1000000000,  # Placeholder
            "load_duration": 0,
            "prompt_eval_count": len(prompt),
            "prompt_eval_duration": 500000000,  # Placeholder
            "eval_count": len(response),
            "eval_duration": 500000000  # Placeholder
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error communicating with Telegram: {str(e)}")

# Function to wait for bot response using Telethon events


async def wait_for_bot_response(client, bot, chat_id):
    """Wait for and return a response from the bot using Telethon events."""
    response_future = asyncio.Future()

    @client.on(events.NewMessage(from_users=bot.id))
    async def response_handler(event):
        response_future.set_result(event.message.text)
        # Remove this handler after getting the response
        client.remove_event_handler(response_handler)

    # Wait for the future to be resolved by the event handler
    try:
        # Add a timeout to prevent hanging indefinitely
        response = await asyncio.wait_for(response_future, timeout=60)
        return response
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504, detail="Timed out waiting for bot response")
    finally:
        # Ensure the handler is removed if we exit due to a timeout
        if not response_future.done():
            client.remove_event_handler(response_handler)

# Chat completion endpoint (Ollama compatible)


@app.post("/api/chat")
async def chat_completion(request: ChatRequest, background_tasks: BackgroundTasks):
    # Extract the last user message
    last_user_message = next((m.content for m in reversed(
        request.messages) if m.role == "user"), None)

    if not last_user_message:
        raise HTTPException(status_code=400, detail="No user message found")

    # Extract conversation ID from options if available
    conversation_id = None
    if request.options and "conversation_id" in request.options:
        conversation_id = request.options["conversation_id"]

    # For non-streaming response
    if not request.stream:
        response = await send_and_get_response(last_user_message, conversation_id)
        return {
            "model": "telegram",
            "created_at": response["created_at"],
            "message": {"role": "assistant", "content": response["response"]},
            "done": True,
            # Return the conversation ID for continuity
            "conversation_id": response["conversation_id"],
            "log_file": response["log_file"],  # Return the log file path
            "total_duration": response["total_duration"],
            "load_duration": 0,
            "prompt_eval_duration": response["prompt_eval_duration"],
            "eval_duration": response["eval_duration"],
            "eval_count": response["eval_count"],
        }
    else:
        # Implementing streaming would require a more complex setup with SSE
        # This is a simplified version
        raise HTTPException(
            status_code=501, detail="Streaming not implemented in this example")

# Generate endpoint (Ollama compatible)


@app.post("/api/generate")
async def generate(request: GenerateRequest, background_tasks: BackgroundTasks):
    # Extract conversation ID from options if available
    conversation_id = None
    if request.options and "conversation_id" in request.options:
        conversation_id = request.options["conversation_id"]

    if not request.stream:
        response = await send_and_get_response(request.prompt, conversation_id)
        return response
    else:
        # Implementing streaming would require a more complex setup with SSE
        # This is a simplified version
        raise HTTPException(
            status_code=501, detail="Streaming not implemented in this example")

# Additional endpoints for chat history


@app.get("/api/history")
async def get_history_list():
    """Get a list of all chat history files."""
    history_dir = Path("history")
    if not history_dir.exists():
        return {"history": []}

    files = []
    for file in sorted(history_dir.glob("*.md"), reverse=True):
        if file.is_file():
            date_chat = file.stem.split("_chat_")
            if len(date_chat) == 2:
                date = date_chat[0]
                chat_num = date_chat[1]
                files.append({
                    "date": date,
                    "chat_number": chat_num,
                    "filename": file.name,
                    "path": str(file)
                })

    return {"history": files}


@app.get("/api/history/{date}/{chat_number}")
async def get_chat_history(date: str, chat_number: str):
    """Get the content of a specific chat history file."""
    filename = f"{date}_chat_{chat_number}.md"
    file_path = Path("history") / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Chat history not found")

    content = file_path.read_text(encoding="utf-8")
    json_path = file_path.with_suffix('.json')

    if json_path.exists():
        json_content = json.loads(json_path.read_text(encoding="utf-8"))
        return {
            "filename": filename,
            "content": content,
            "messages": json_content["messages"] if "messages" in json_content else []
        }

    return {
        "filename": filename,
        "content": content,
        "messages": []
    }

if __name__ == "__main__":
    # Create history directory if it doesn't exist
    history_dir = Path("history")
    history_dir.mkdir(exist_ok=True)

    import uvicorn
    uvicorn.run(app, host=API_HOST, port=API_PORT)
