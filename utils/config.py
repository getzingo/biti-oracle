import os
from dataclasses import dataclass
from dotenv import load_dotenv
from pathlib import Path
import yaml

load_dotenv(Path(__file__).parent.parent / "env")
with open("config.yaml", "r") as f:
    yaml_config = yaml.safe_load(f)

@dataclass(frozen=True)
class Config:
    oracle_api_server_url: str = os.getenv("ORACLE_API_SERVER_URL")
    oracle_api_server_token: str = os.getenv("ORACLE_API_SERVER_TOKEN")
    oai_url: str = os.getenv("OAI_COMPATIBLE_API_URL")
    oai_token: str = os.getenv("OAI_COMPATIBLE_API_TOKEN")
    llm_model_name: str = os.getenv("OAI_MODEL", None)
    llm_backup_model_name: str = os.getenv("OAI_BACKUP_MODEL", None)
    allow_external_llm: bool = os.getenv("ALLOW_EXTERNAL_LLM", False)
    db_storage: str = "storage"
    inference_timeout_seconds: int = 60
    sensing_min_duration_seconds: int = 3
    sensing_max_duration_seconds: int = 15
    sensing_messages = yaml_config.get("SENSING_MESSAGES", ["The Oracle ponders..."])
    display_fortune_duration_seconds: int = 30
    dev_mode: bool = os.getenv("DEV_MODE", "false").lower() in ["true", "1", "t", "yes"]
config = Config()