$log = "bot_out.txt"
$err = "bot_err.txt"
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUNBUFFERED = "1"
$date = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
"[$date] Starting bot..." | Out-File $log -Encoding utf8
try {
    $p = Start-Process -FilePath "python" `
        -ArgumentList "bot.py" `
        -NoNewWindow -PassThru
    "`n[$date] PID: $($p.Id)" | Out-File $log -Encoding utf8 -Append
    Wait-Process -Id $p.Id
    $exitCode = $p.ExitCode
    "`n[$date] Bot exited with code: $exitCode" | Out-File $log -Encoding utf8 -Append
} catch {
    "`n[$date] Error: $_" | Out-File $log -Encoding utf8 -Append
}
