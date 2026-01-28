# W3-5 Full Demo Scenario Execution Script
# Full scenario: Seed -> Agent Run (Mixed Intent)

# Set UTF-8 encoding
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

$baseUrl = "http://localhost:8000"
$adminToken = "dev-admin-token"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  TRACE-AI Full Demo Scenario Execution" -ForegroundColor Cyan
Write-Host "  W3-5 Demo Rehearsal" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Backend server health check
Write-Host "[Step 1/3] Checking Backend server status..." -ForegroundColor Yellow
try {
    $healthResponse = curl.exe -s -X GET "$baseUrl/health"
    if ($LASTEXITCODE -eq 0) {
        Write-Host "OK Backend server is running" -ForegroundColor Green
    } else {
        Write-Host "ERROR Backend server not responding. Please start the server first." -ForegroundColor Red
        Write-Host "  Command: uvicorn app.main:app --reload" -ForegroundColor Yellow
        exit 1
    }
} catch {
    Write-Host "ERROR Backend server connection failed" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Step 2: Demo document seeding (upload to knowledge store)
Write-Host "[Step 2/3] Running demo document seeding..." -ForegroundColor Yellow
Write-Host ""

# Move to project root (script is in scripts/, so go up one level)
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptDir
Set-Location $projectRoot

# Execute seed script
& "$scriptDir\seed_demo_docs.ps1"

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR Document seeding failed" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "OK Document seeding completed" -ForegroundColor Green
Write-Host ""

# Step 3: Agent Run (Mixed Intent scenario)
Write-Host "[Step 3/3] Executing Agent Run (Mixed Intent)..." -ForegroundColor Yellow
Write-Host ""

# Use demo_request_mixed.json directly (avoid PowerShell encoding issues)
$jsonPath = Join-Path $projectRoot "demo_request_mixed.json"
if (-not (Test-Path $jsonPath)) {
    Write-Host "ERROR: demo_request_mixed.json not found." -ForegroundColor Red
    exit 1
}

Write-Host "Request file: demo_request_mixed.json" -ForegroundColor Cyan
Get-Content $jsonPath -Raw -Encoding UTF8 | Write-Host
Write-Host ""

Write-Host "Running Agent..." -ForegroundColor Yellow
$agentResponse = curl.exe -X POST "$baseUrl/api/v1/agent/run" `
    -H "Content-Type: application/json" `
    -d "@$jsonPath"

Write-Host ""
Write-Host "=== Agent Run Response ===" -ForegroundColor Cyan
Write-Host $agentResponse
Write-Host ""

# Extract run_id from response (simple parsing)
if ($agentResponse -match '"run_id"\s*:\s*"([^"]+)"') {
    $runId = $matches[1]
    Write-Host "OK Agent Run completed" -ForegroundColor Green
    Write-Host "  run_id: $runId" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Audit summary query:" -ForegroundColor Yellow
    Write-Host "  curl.exe -X GET `"$baseUrl/api/v1/runs/$runId/audit`"" -ForegroundColor Gray
} else {
    Write-Host "WARNING run_id not found. Please check the response." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Full Demo Scenario Execution Complete" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
