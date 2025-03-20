from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Union
import asyncio
import json
import uuid
import datetime
from pathlib import Path
import time
from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError
import logging

# Import configuration
from config import (
    API_ID, API_HASH, BOT_USERNAME, get_proxy_settings,
    SESSION_NAME, API_HOST, API_PORT
)
from chat_logger import ChatLogger

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("telegram_api.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("telegram-api")

# Initialize FastAPI
app = FastAPI(title="Telegram LLM API")

# Add CORS middleware to allow requests from any origin
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


class ModelOptions(BaseModel):
    num_keep: Optional[int] = None
    seed: Optional[int] = None
    num_predict: Optional[int] = None
    top_k: Optional[int] = None
    top_p: Optional[float] = None
    min_p: Optional[float] = None
    typical_p: Optional[float] = None
    repeat_last_n: Optional[int] = None
    temperature: Optional[float] = None
    repeat_penalty: Optional[float] = None
    presence_penalty: Optional[float] = None
    frequency_penalty: Optional[float] = None
    mirostat: Optional[int] = None
    mirostat_tau: Optional[float] = None
    mirostat_eta: Optional[float] = None
    penalize_newline: Optional[bool] = None
    stop: Optional[List[str]] = None
    num_ctx: Optional[int] = None
    num_thread: Optional[int] = None
    conversation_id: Optional[str] = None


class GenerateRequest(BaseModel):
    model: str
    prompt: str
    system: Optional[str] = None
    template: Optional[str] = None
    context: Optional[List[int]] = None
    options: Optional[ModelOptions] = None
    format: Optional[Union[str, Dict[str, Any]]] = None
    raw: Optional[bool] = False
    stream: Optional[bool] = None
    keep_alive: Optional[str] = "5m"
    suffix: Optional[str] = None
    images: Optional[List[str]] = None


class ToolCallFunction(BaseModel):
    name: str
    arguments: Dict[str, Any]


class ToolCall(BaseModel):
    id: Optional[str] = None
    type: Optional[str] = "function"
    function: ToolCallFunction


class ChatMessage(BaseModel):
    role: str
    content: str
    images: Optional[List[str]] = None
    tool_calls: Optional[List[ToolCall]] = None


class FunctionParameter(BaseModel):
    type: str
    description: Optional[str] = None
    enum: Optional[List[str]] = None
    properties: Optional[Dict[str, Any]] = None
    required: Optional[List[str]] = None


class FunctionDefinition(BaseModel):
    name: str
    description: Optional[str] = None
    parameters: FunctionParameter


class Tool(BaseModel):
    type: str = "function"
    function: FunctionDefinition


class ChatRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    stream: Optional[bool] = None
    tools: Optional[List[Tool]] = None
    options: Optional[ModelOptions] = None
    keep_alive: Optional[str] = "5m"
    format: Optional[Union[str, Dict[str, Any]]] = None


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
        logger.error(
            "Telegram API credentials not found in environment variables.")
        logger.error(
            "Please set TELEGRAM_API_ID and TELEGRAM_API_HASH in your .env file.")
        import sys
        sys.exit(1)

    if not BOT_USERNAME:
        logger.warning(
            "TELEGRAM_BOT_USERNAME not set. This is required for the API to work properly.")

    app.telegram_client = None
    await get_client()
    logger.info(f"Telegram API server started on {API_HOST}:{API_PORT}")
    logger.info(f"Using proxy: {get_proxy_settings() is not None}")


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
    """List models that are available locally."""
    return {
        "models": [
            {
                "name": "telegram",
                "modified_at": datetime.datetime.now().isoformat(),
                "size": 0,
                "digest": "telegram-bot",
                "details": {
                    "format": "telegram",
                    "family": "telegram",
                    "families": ["telegram"],
                    "parameter_size": "Unknown",
                    "quantization_level": "None"
                }
            }
        ]
    }


@app.get("/api/version")
async def get_version():
    """Return the version information."""
    return {
        "version": "1.0.0"
    }


@app.get("/api/ps")
async def list_running_models():
    """List models that are currently loaded into memory."""
    # In Telegram's case, we don't actually load models, but we'll mimic the API
    return {
        "models": [
            {
                "name": "telegram",
                "model": "telegram",
                "size": 0,
                "digest": "telegram-bot",
                "details": {
                    "parent_model": "",
                    "format": "telegram",
                    "family": "telegram",
                    "families": ["telegram"],
                    "parameter_size": "Unknown",
                    "quantization_level": "None"
                },
                "expires_at": (datetime.datetime.now() + datetime.timedelta(minutes=5)).isoformat(),
                "size_vram": 0
            }
        ]
    }


# Helper function to send message and get response from Telegram
async def send_and_get_response(prompt, system=None, conversation_id=None, model="telegram"):
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

        # If system prompt is provided, prepend it to the prompt
        full_prompt = prompt
        if system:
            full_prompt = f"[SYSTEM]: {system}\n\n{prompt}"

        # Log the user message
        logger.log_user_message(full_prompt)

        start_time = time.time()
        prompt_length = len(full_prompt)

        # Send the message
        await client.send_message(bot, full_prompt)

        # Wait for response using the proper events mechanism
        response, elapsed_prompt_time = await wait_for_bot_response(client, bot, conversation_id)

        end_time = time.time()
        total_duration = int((end_time - start_time) *
                             1_000_000_000)  # Convert to nanoseconds
        response_length = len(response)

        # Log the bot response
        logger.log_bot_message(response)

        # Save the conversation
        logger.save_json()

        return {
            "model": model,
            "created_at": datetime.datetime.now().isoformat(),
            "response": response,
            "done": True,
            # Placeholder context (Ollama uses this for conversation memory)
            "context": [1, 2, 3],
            "total_duration": total_duration,
            "load_duration": 0,  # No loading phase in Telegram
            "prompt_eval_count": prompt_length,
            "prompt_eval_duration": elapsed_prompt_time,
            "eval_count": response_length,
            "eval_duration": total_duration - elapsed_prompt_time,
            # Extra fields for our implementation
            "conversation_id": conversation_id,
            "log_file": logger.get_filename(),
        }
    except Exception as e:
        logger.error(f"Error communicating with Telegram: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error communicating with Telegram: {str(e)}")


# Function to wait for bot response using Telethon events
async def wait_for_bot_response(client, bot, chat_id):
    """Wait for and return a response from the bot using Telethon events."""
    response_future = asyncio.Future()
    start_time = time.time()

    @client.on(events.NewMessage(from_users=bot.id))
    async def response_handler(event):
        elapsed_time = int((time.time() - start_time) *
                           1_000_000_000)  # Convert to nanoseconds
        response_future.set_result((event.message.text, elapsed_time))
        # Remove this handler after getting the response
        client.remove_event_handler(response_handler)

    # Wait for the future to be resolved by the event handler
    try:
        # Add a timeout to prevent hanging indefinitely
        response, elapsed_time = await asyncio.wait_for(response_future, timeout=180)
        return response, elapsed_time
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504, detail="Timed out waiting for bot response")
    finally:
        # Ensure the handler is removed if we exit due to a timeout
        if not response_future.done():
            client.remove_event_handler(response_handler)


# Chat completion endpoint (Ollama compatible)
@app.post("/api/chat")
async def chat_completion(request: ChatRequest):
    """Generate the next message in a chat with a provided model."""
    # Extract conversation ID from options if available
    conversation_id = None
    if request.options and hasattr(request.options, "conversation_id"):
        conversation_id = request.options.conversation_id

    # Get system message if there is one
    system_message = None
    for msg in request.messages:
        if msg.role == "system":
            system_message = msg.content
            break

    # Extract the last user message
    last_user_message = None
    for msg in reversed(request.messages):
        if msg.role == "user":
            last_user_message = msg.content
            break

    if not last_user_message:
        raise HTTPException(status_code=400, detail="No user message found")

    # Process images if they exist (for multimodal models)
    # Note: This would require additional implementation for Telegram bots that support images
    images = []
    for msg in request.messages:
        if msg.role == "user" and msg.images:
            images.extend(msg.images)

    # Handle empty messages array - just load the model and return
    if len(request.messages) == 0:
        return {
            "model": request.model,
            "created_at": datetime.datetime.now().isoformat(),
            "message": {
                "role": "assistant",
                "content": ""
            },
            "done_reason": "load",
            "done": True
        }

    # Check if this is a request to unload the model
    if len(request.messages) == 0 and request.keep_alive == "0":
        return {
            "model": request.model,
            "created_at": datetime.datetime.now().isoformat(),
            "message": {
                "role": "assistant",
                "content": ""
            },
            "done_reason": "unload",
            "done": True
        }

    # Send the message and get the response
    response = await send_and_get_response(
        last_user_message,
        system=system_message,
        conversation_id=conversation_id,
        model=request.model
    )

    # Format the response according to the Ollama API
    return {
        "model": request.model,
        "created_at": response["created_at"],
        "message": {
            "role": "assistant",
            "content": response["response"],
            "images": None
        },
        "done": True,
        "total_duration": response["total_duration"],
        "load_duration": response["load_duration"],
        "prompt_eval_count": response["prompt_eval_count"],
        "prompt_eval_duration": response["prompt_eval_duration"],
        "eval_count": response["eval_count"],
        "eval_duration": response["eval_duration"],
        # Extra fields for our implementation
        "conversation_id": response["conversation_id"],
        "log_file": response["log_file"]
    }


# Generate endpoint (Ollama compatible)
@app.post("/api/generate")
async def generate(request: GenerateRequest):
    """Generate a response for a given prompt with a provided model."""
    # Extract conversation ID from options if available
    conversation_id = None
    if request.options and hasattr(request.options, "conversation_id"):
        conversation_id = request.options.conversation_id

    # Check if this is a request to unload the model
    if not request.prompt and request.keep_alive == "0":
        return {
            "model": request.model,
            "created_at": datetime.datetime.now().isoformat(),
            "response": "",
            "done": True,
            "done_reason": "unload"
        }

    # Check if this is just loading the model
    if not request.prompt:
        return {
            "model": request.model,
            "created_at": datetime.datetime.now().isoformat(),
            "response": "",
            "done": True
        }

    # Send the message and get the response
    response = await send_and_get_response(
        request.prompt,
        system=request.system,
        conversation_id=conversation_id,
        model=request.model
    )

    # Format the response according to the Ollama API
    return {
        "model": request.model,
        "created_at": response["created_at"],
        "response": response["response"],
        "done": True,
        "context": response["context"],
        "total_duration": response["total_duration"],
        "load_duration": response["load_duration"],
        "prompt_eval_count": response["prompt_eval_count"],
        "prompt_eval_duration": response["prompt_eval_duration"],
        "eval_count": response["eval_count"],
        "eval_duration": response["eval_duration"],
        # Extra fields for our implementation
        "conversation_id": response["conversation_id"],
        "log_file": response["log_file"]
    }


@app.post("/api/embeddings")
@app.post("/api/embed")
async def generate_embeddings(request: Request):
    """
    Generate embeddings from a model.

    Note: This is a placeholder implementation as most Telegram bots don't provide embeddings.
    You might want to replace this with a call to a real embedding model if needed.
    """
    data = await request.json()
    model = data.get("model", "telegram")
    input_text = data.get("input", "")  # Can be a string or list of strings

    # Create simple mock embeddings (random values between -1 and 1)
    # In a real implementation, you'd use an actual embedding model
    import random

    def create_mock_embedding(dimension=384):
        return [random.uniform(-1, 1) for _ in range(dimension)]

    if isinstance(input_text, list):
        embeddings = [create_mock_embedding() for _ in input_text]
    else:
        embeddings = [create_mock_embedding()]

    return {
        "model": model,
        "embeddings": embeddings,
        "total_duration": 10000000,  # Mock duration in nanoseconds
        "load_duration": 1000000,
        "prompt_eval_count": len(input_text) if isinstance(input_text, str) else sum(len(t) for t in input_text)
    }


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
