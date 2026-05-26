import json
from pathlib import Path
from typing import Any

from faster_whisper import WhisperModel


class Transcriber:
    def __init__(self, model_size: str = "base", device: str = "auto",
                 compute_type: str = "int8", logger: Any = None):
        self.log = logger
        self._model: WhisperModel | None = None
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type

    def _get_model(self) -> WhisperModel:
        if self._model is None:
            if self.log:
                self.log(f"Loading faster-whisper model '{self.model_size}' (device={self.device})")
            self._model = WhisperModel(self.model_size, device=self.device, compute_type=self.compute_type)
        return self._model

    def transcribe(self, audio_path: str | Path) -> dict:
        model = self._get_model()
        audio_path = str(audio_path)

        if self.log:
            self.log(f"Transcribing: {audio_path}")

        segments, info = model.transcribe(audio_path, beam_size=5)

        segment_list = []
        full_text_parts = []

        for seg in segments:
            segment_list.append({
                "start": round(seg.start, 2),
                "end": round(seg.end, 2),
                "text": seg.text.strip(),
            })
            full_text_parts.append(seg.text.strip())

        full_text = " ".join(full_text_parts)

        result = {
            "text": full_text,
            "language": info.language,
            "duration_seconds": round(info.duration, 2) if info.duration else None,
            "segments": segment_list,
            "model_used": self.model_size,
        }

        if self.log:
            self.log(f"Transcription complete: {len(segment_list)} segments, "
                     f"{len(full_text)} chars, language={info.language}")

        return result

    def save_transcript(self, result: dict, output_dir: str | Path,
                        source_id: int | str) -> dict[str, str]:
        output_dir = Path(output_dir)
        subdir = output_dir / str(source_id)
        subdir.mkdir(parents=True, exist_ok=True)

        txt_path = subdir / "transcript.txt"
        txt_path.write_text(result["text"], encoding="utf-8")

        json_path = subdir / "transcript.json"
        json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

        return {"txt": str(txt_path), "json": str(json_path)}
