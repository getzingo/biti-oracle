import logging
import asyncio
import hmac
import hashlib
import json

from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks, Depends
from pathlib import Path
import os
import uuid
import openai
import re
from utils.api.UsedFortunes import UsedFortunes
from utils.classes.Fortune import Fortune
from utils.config import config

try:
    from oracllm import return_slug
except ImportError:
    def return_slug():
        return "dummy-slug"

env_path = Path(__file__).resolve().parent / 'env'
load_dotenv(env_path)

DEV_MODE = config.dev_mode
oracle_api_token = os.getenv("ORACLE_API_SERVER_TOKEN", "")

app = FastAPI()
if DEV_MODE:
     logging.basicConfig(level=logging.DEBUG)
else:
    logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

logger.info(f"DEV_MODE: {DEV_MODE}")

allowed_commands = {"ping", "oracle", "dummy"}
tasks_status = {}
used_fortunes = UsedFortunes()


def _strip_thinking(text: str) -> str:
    """Remove <think>...</think> blocks that some models emit before the answer."""
    text = re.sub(r'<think>[\s\S]*?</think>', '', text, flags=re.IGNORECASE)
    return text.strip()

oai_url = os.getenv("OAI_COMPATIBLE_API_URL", "")
lllm_token = os.getenv("LLLM_TOKEN", "")

assert lllm_token != ""
assert oai_url != ""

openai_client = openai.AsyncOpenAI(api_key=lllm_token, base_url=oai_url) if (lllm_token and oai_url) else None

async def get_fortune(instructions: str) -> str:
    instructions += used_fortunes.get_todays_fortunes()

    if not openai_client:
        raise Exception("lllm_token not set, aborting task")
    response = await openai_client.chat.completions.create(
        model=os.getenv("OAI_MODEL"),
        messages=[
            {"role": "system", "content": instructions},
            {"role": "user", "content": "Speak."}
        ]
    )
    result = _strip_thinking(response.choices[0].message.content)
    nf = Fortune()
    nf.mood = "unknown"
    nf.add_fortune(result)
    used_fortunes.store_fortune(nf)
    return result

def verify_signature(payload: bytes, signature: str) -> bool:
    if not oracle_api_token:
        return False
    expected = hmac.new(
        oracle_api_token.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)

async def start_inference(task_id: str, data: dict):
    logger.info(f"Starting inference for task {task_id} and data: {data}")
    tasks_status[task_id] = {"status": "running"}

    try:
        answer = await asyncio.wait_for(
            get_fortune(data["mood"]),
            timeout=config.inference_timeout_seconds,
        )
        tasks_status[task_id] = {"status": "completed", "result": answer}
    except asyncio.TimeoutError:
        logger.error(f"Timeout for inference task {task_id}")
        tasks_status[task_id] = {"status": "failed", "result": None}

    except Exception as e:
        logger.error(f"Exception during inference task {task_id} with {e}")
        tasks_status[task_id] = {"status": "failed", "result": str(e)}

async def auth_dependency(request: Request):
    if DEV_MODE:
        return
    # GET has no body — sign the URL path instead
    payload = request.url.path.encode()
    signature = request.headers.get("X-Hub-Signature-256", "")
    if not signature or not verify_signature(payload, signature):
        logger.error("Invalid signature, request denied")
        raise HTTPException(status_code=403, detail="Invalid signature")

@app.post("/")
async def webhook(request: Request, bg_tasks: BackgroundTasks):
    body = await request.body()

    if not DEV_MODE:
        signature = request.headers.get("X-Hub-Signature-256", "")
        if not signature or not verify_signature(body, signature):
            logger.error("Invalid signature, request denied")
            raise HTTPException(status_code=403, detail="Invalid signature")

    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    action = data.get("action")
    payload_data = data.get("data", {})

    if not action or action not in allowed_commands:
        logger.error(f"Invalid or missing action provided: {action}")
        raise HTTPException(status_code=400, detail="Invalid action provided")

    if action == "dummy":
        return {"status": "slug requested", "action": action, "result": return_slug()}

    if action == "oracle":
        task_id = str(uuid.uuid4())
        logger.debug(f"{action} requested, starting task {task_id}")
        tasks_status[task_id] = {"status": "pending"}
        bg_tasks.add_task(start_inference, task_id, payload_data)
        return {"status": "task accepted", "task_id": task_id}

    return {"status": "success", "action": action}

@app.get("/status/{task_id}", dependencies=[Depends(auth_dependency)])
async def get_status(task_id: str):
    if task_id not in tasks_status:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"task_id": task_id, **tasks_status[task_id]}

@app.get("/ping")
async def ping():
    return {"pong"}
