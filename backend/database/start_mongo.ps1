
# Start MongoDB Service
Write-Host "Starting MongoDB Service..."
try {
    Start-Service MongoDB
    Write-Host "✅ MongoDB Service Started Successfully!" -ForegroundColor Green
} catch {
    Write-Host "❌ Failed to start service automatically. Attempting manual start..." -ForegroundColor Red
    
    # Try finding the executable manually if service fails
    $mongoPaths = @(
        "C:\Program Files\MongoDB\Server\7.0\bin\mongod.exe",
        "C:\Program Files\MongoDB\Server\6.0\bin\mongod.exe",
        "C:\Program Files\MongoDB\Server\5.0\bin\mongod.exe",
        "C:\Program Files\MongoDB\Server\4.4\bin\mongod.exe"
    )
    
    foreach ($path in $mongoPaths) {
        if (Test-Path $path) {
            Write-Host "Found MongoDB at: $path"
            Write-Host "Starting mongod..."
            Start-Process -FilePath $path -ArgumentList "--dbpath", "C:\data\db" -NoNewWindow
            Write-Host "✅ MongoDB Started!" -ForegroundColor Green
            exit
        }
    }
    
    Write-Host "❌ Could not find mongod.exe. Please install MongoDB or start it manually." -ForegroundColor Red
}
