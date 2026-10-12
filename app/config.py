from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    llm_base_url: str = "http://localhost:11434/v1"
    llm_api_key: str = "ollama"
    llm_model: str = "qwen3:4b"
    llm_disable_thinking: bool = True
    llm_temperature: float = 0.1
    llm_num_ctx: int = 4096

    agent_max_steps: int = 5
    ml_scoring_url: str = ""

    default_roi: float = 9.5
    foir_cap: float = 0.50

settings = Settings()
