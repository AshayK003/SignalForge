from pathlib import Path
from typing import Any


PROMPT_DIR = Path(__file__).parent.parent.parent / "prompts"


class PromptLibrary:
    def __init__(self, prompt_dir: str | Path = PROMPT_DIR):
        self.prompt_dir = Path(prompt_dir)
        self._cache: dict[str, str] = {}

    def load(self, name: str) -> str:
        if name not in self._cache:
            path = self.prompt_dir / f"{name}.md"
            if not path.exists():
                raise FileNotFoundError(f"Prompt template not found: {path}")
            self._cache[name] = path.read_text(encoding="utf-8")
        return self._cache[name]

    def render(self, name: str, **kwargs: Any) -> str:
        template = self.load(name)
        return template.format(**kwargs)
