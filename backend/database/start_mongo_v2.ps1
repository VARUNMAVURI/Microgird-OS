
# Start MongoDB (Manually found path)
$mongoPath = "C:\Program Files\MongoDB\Server\8.2\bin\mongod.exe"
$dbPath = "C:\data\db"

Write-Host "Creating data directory at $dbPath..."
if (-not (Test-Path $dbPath)) {
    New-Item -ItemType Directory -Force -Path $dbPath | Out-Null
}

if (Test-Path $mongoPath) {
    Write-Host "Found MongoDB at: $mongoPath"
    Write-Host "Starting mongod..."
    Start-Process -FilePath $mongoPath -ArgumentList "--dbpath", "`"$dbPath`"" -NoNewWindow
    Write-Host "✅ MongoDB Started! Keeps running in background." -ForegroundColor Green
} else {
    Write-Host "❌ Still could not find mongod.exe at expected path: $mongoPath" -ForegroundColor Red
}
