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
    openrouter_model: str = "deepseek/deepseek-v4-flash:free"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"
    deepseek_api_key: str = ""
    deepseek_model: str = "deepseek-chat"
    max_rpm: int = 20


@dataclass
class DepsConfig:
    deno_path: str = ""
    ffmpeg_path: str = ""
    tesseract_cmd: str = ""
    poppler_bin: str = ""


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
    deps: DepsConfig = field(default_factory=DepsConfig)


def load_config(config_path: str | None = None) -> Config:
    load_dotenv()
    cfg = Config()

    yaml_path = config_path or os.getenv("SIGNALFORGE_CONFIG", "config.yaml")
    yaml_file = Path(yaml_path)
    if yaml_file.exists():
        with open(yaml_file) as f:
            raw = yaml.safe_load(f) or {}
        for section in ["app", "chunking", "transcription", "report", "logging", "deps"]:
            cls_name = section.capitalize() + "Config"
            cls = globals().get(cls_name)
            if section in raw and cls:
                setattr(cfg, section, cls(**{**getattr(cfg, section).__dict__, **raw[section]}))

    cfg.llm.provider = os.getenv("LLM_PROVIDER", cfg.llm.provider)
    cfg.llm.openrouter_api_key = os.getenv("OPENROUTER_API_KEY", "")
    cfg.llm.openrouter_model = os.getenv("OPENROUTER_MODEL", cfg.llm.openrouter_model)
    cfg.llm.ollama_base_url = os.getenv("OLLAMA_BASE_URL", cfg.llm.ollama_base_url)
    cfg.llm.ollama_model = os.getenv("OLLAMA_MODEL", cfg.llm.ollama_model)
    cfg.llm.deepseek_api_key = os.getenv("DEEPSEEK_API_KEY", "")
    cfg.llm.deepseek_model = os.getenv("DEEPSEEK_MODEL", cfg.llm.deepseek_model)
    cfg.rclone.remote = os.getenv("RCLONE_REMOTE", cfg.rclone.remote)
    cfg.rclone.path = os.getenv("RCLONE_PATH", cfg.rclone.path)

    from app.utils.deps import configure as configure_deps
    configure_deps(
        deno_path=cfg.deps.deno_path or None,
        ffmpeg_path=cfg.deps.ffmpeg_path or None,
        tesseract_cmd=cfg.deps.tesseract_cmd or None,
        poppler_bin=cfg.deps.poppler_bin or None,
    )

    if cfg.llm.provider == "openrouter" and not cfg.llm.openrouter_api_key:
        print("WARNING: LLM_PROVIDER is 'openrouter' but OPENROUTER_API_KEY is not set.")
        print("Set it in .env or switch LLM_PROVIDER to 'ollama' or 'deepseek'.")
    if cfg.llm.provider == "deepseek" and not cfg.llm.deepseek_api_key:
        print("WARNING: LLM_PROVIDER is 'deepseek' but DEEPSEEK_API_KEY is not set.")

    return cfg
