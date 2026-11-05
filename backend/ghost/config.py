from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    mode: Literal["demo", "imessage"] = "demo"
    data_dir: Path = Path("data")
    api_token: str = ""
    llm: bool = False
    llm_provider: Literal["openai", "ollama"] = "openai"
    ollama_url: str = "http://127.0.0.1:11434"
    openai_api_key: SecretStr | None = Field(default=None, validation_alias="OPENAI_API_KEY")
    model: str = "gpt-4.1-mini"
    allowed_recipients: list[str] = []
    send_enabled: bool = False
    mcp_command: str = "uv"
    mcp_args: list[str] = [
        "run",
        "--no-project",
        "--with",
        "git+https://github.com/carterlasalle/mac_messages_mcp.git@8eae89d9d9eae97333f4401ef47393d5e35f58ab",
        "python",
        str(Path(__file__).with_name("mcp_server.py")),
    ]
    model_config = SettingsConfigDict(env_prefix="GHOST_", env_file=".env", extra="ignore")
