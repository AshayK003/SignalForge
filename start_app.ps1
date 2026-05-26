$denoPath = "C:\Users\Ashay\AppData\Local\Microsoft\WinGet\Packages\DenoLand.Deno_Microsoft.Winget.Source_8wekyb3d8bbwe"
$ffmpegPath = "C:\Users\Ashay\AppData\Local\Microsoft\WinGet\Packages\yt-dlp.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-N-124279-g0f6ba39122-win64-gpl\bin"
$popplerPath = "C:\Users\Ashay\AppData\Local\Microsoft\WinGet\Packages\oschwartz10612.Poppler_Microsoft.Winget.Source_8wekyb3d8bbwe\poppler-25.07.0\Library\bin"
$tesseractPath = "C:\Program Files\Tesseract-OCR"
$env:PATH = "$denoPath;$ffmpegPath;$popplerPath;$tesseractPath;$env:PATH"
$env:PYTHONUNBUFFERED = 1
python -m streamlit run "D:\Personal projects\SignalForge\streamlit_app.py"
