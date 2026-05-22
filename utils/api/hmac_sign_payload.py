from utils.config import config
import hmac
import hashlib

def sign_payload(payload_bytes: bytes) -> str:
    api_key = config.oracle_api_server_token
    if not api_key:
        return ""
    expected = hmac.new(
        api_key.encode(),
        payload_bytes,
        hashlib.sha256
    ).hexdigest()
    return f"sha256={expected}"