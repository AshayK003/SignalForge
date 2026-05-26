import os


def _env_path(key: str) -> str | None:
    v = os.environ.get(key, "").strip()
    return v if v else None


DENO_PATH = _env_path("SIGNALFORGE_DENO_PATH") or ""
FFMPEG_PATH = _env_path("SIGNALFORGE_FFMPEG_PATH") or ""
TESSERACT_CMD = _env_path("SIGNALFORGE_TESSERACT_CMD") or ""
POPPLER_BIN = _env_path("SIGNALFORGE_POPPLER_BIN") or ""


def configure(*, deno_path=None, ffmpeg_path=None, tesseract_cmd=None, poppler_bin=None):
    d = globals()
    if deno_path is not None:
        d["DENO_PATH"] = deno_path
    if ffmpeg_path is not None:
        d["FFMPEG_PATH"] = ffmpeg_path
    if tesseract_cmd is not None:
        d["TESSERACT_CMD"] = tesseract_cmd
    if poppler_bin is not None:
        d["POPPLER_BIN"] = poppler_bin


def extended_env() -> dict:
    env = os.environ.copy()
    paths = [p for p in [DENO_PATH, FFMPEG_PATH] if p]
    env_path = env.get("PATH", "")
    for p in paths:
        if p not in env_path:
            env_path = f"{p};{env_path}"
    env["PATH"] = env_path
    return env


def ensure_local_paths():
    for p in [DENO_PATH, FFMPEG_PATH]:
        if p and p not in os.environ.get("PATH", "") and os.path.isdir(p):
            os.environ["PATH"] = p + os.pathsep + os.environ.get("PATH", "")
    if POPPLER_BIN and os.path.isdir(POPPLER_BIN) and POPPLER_BIN not in os.environ.get("PATH", ""):
        os.environ["PATH"] = POPPLER_BIN + os.pathsep + os.environ.get("PATH", "")
    if TESSERACT_CMD:
        import pytesseract
        pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD
        if not os.path.exists(TESSERACT_CMD):
            raise RuntimeError(
                "Tesseract OCR engine not found. "
                "Set SIGNALFORGE_TESSERACT_CMD or install Tesseract from: "
                "https://github.com/UB-Mannheim/tesseract/releases"
            )
