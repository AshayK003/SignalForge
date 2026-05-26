import os
import yaml
from pathlib import Path
from dataclasses import dataclass, field
from dotenv import load_dotenv


@dataclass
class ChunkingConfig:
    max_chunk_size: int = 3000
    overlap: int = 300


@dataclass
class TranscriptionConfig:
    model: str = "base"
    device: str = "auto"
    compute_type: str = "int8"


@dataclass
class ReportConfig:
    max_sources_per_report: int = 50
    output_formats: list[str] = field(default_factory=lambda: ["pdf", "markdown"])


@dataclass
class AppConfig:
    name: str = "SignalForge"
    version: str = "0.1.0"
    data_dir: str = "./data"


@dataclass
class LoggingConfig:
    level: str = "INFO"
    file: str = "./data/signalforge.log"


@dataclass
class LLMConfig:
    provider: str = "openrouter"
    openrouter_api_key: str = ""
    openrouter_model: str = "google/gemini-2.0-flash-001"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"


@dataclass
class RcloneConfig:
    remote: str = "mega"
    path: str = "SignalForge"


@dataclass
class Config:
    app: AppConfig = field(default_factory=AppConfig)
    chunking: ChunkingConfig = field(default_factory=ChunkingConfig)
    transcription: TranscriptionConfig = field(default_factory=TranscriptionConfig)
    report: ReportConfig = field(default_factory=ReportConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    rclone: RcloneConfig = field(default_factory=RcloneConfig)


def load_config(config_path: str | None = None) -> Config:
    load_dotenv()
    cfg = Config()

    yaml_path = config_path or os.getenv("SIGNALFORGE_CONFIG", "config.yaml")
    yaml_file = Path(yaml_path)
    if yaml_file.exists():
        with open(yaml_file) as f:
            raw = yaml.safe_load(f) or {}
        if "app" in raw:
            cfg.app = AppConfig(**{**cfg.app.__dict__, **raw["app"]})
        if "chunking" in raw:
            cfg.chunking = ChunkingConfig(**{**cfg.chunking.__dict__, **raw["chunking"]})
        if "transcription" in raw:
            cfg.transcription = TranscriptionConfig(**{**cfg.transcription.__dict__, **raw["transcription"]})
        if "report" in raw:
            cfg.report = ReportConfig(**{**cfg.report.__dict__, **raw["report"]})
        if "logging" in raw:
            cfg.logging = LoggingConfig(**{**cfg.logging.__dict__, **raw["logging"]})

    cfg.llm.provider = os.getenv("LLM_PROVIDER", cfg.llm.provider)
    cfg.llm.openrouter_api_key = os.getenv("OPENROUTER_API_KEY", "")
    cfg.llm.openrouter_model = os.getenv("OPENROUTER_MODEL", cfg.llm.openrouter_model)
    cfg.llm.ollama_base_url = os.getenv("OLLAMA_BASE_URL", cfg.llm.ollama_base_url)
    cfg.llm.ollama_model = os.getenv("OLLAMA_MODEL", cfg.llm.ollama_model)
    cfg.rclone.remote = os.getenv("RCLONE_REMOTE", cfg.rclone.remote)
    cfg.rclone.path = os.getenv("RCLONE_PATH", cfg.rclone.path)

    if cfg.llm.provider == "openrouter" and not cfg.llm.openrouter_api_key:
        print("WARNING: LLM_PROVIDER is 'openrouter' but OPENROUTER_API_KEY is not set.")
        print("Set it in .env or switch LLM_PROVIDER to 'ollama'.")

    return cfg
