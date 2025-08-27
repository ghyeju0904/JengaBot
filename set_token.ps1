# Discord bot token setup script
# This script sets the DISCORD_TOKEN environment variable

Write-Host "Discord Jenga Bot Token Setup" -ForegroundColor Green
Write-Host ""

# Get bot token input
$token = Read-Host "Enter your Discord bot token"

if ($token) {
    # Set environment variable
    $env:DISCORD_TOKEN = $token
    
    Write-Host ""
    Write-Host "Token has been set successfully!" -ForegroundColor Green
    Write-Host "Now run 'python bot.py' to start the bot." -ForegroundColor Yellow
    
    # Ask if user wants to run bot now
    $runBot = Read-Host "Do you want to run the bot now? (y/n)"
    
    if ($runBot -eq "y" -or $runBot -eq "Y") {
        Write-Host "Starting bot..." -ForegroundColor Cyan
        python bot.py
    }
} else {
    Write-Host "No token was entered." -ForegroundColor Red
}
