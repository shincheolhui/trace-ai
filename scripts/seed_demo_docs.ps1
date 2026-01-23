# Demo Document Seeding Script (PowerShell)
# W3-5 Demo Rehearsal

# Set UTF-8 encoding for proper output
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

$baseUrl = "http://localhost:8000"
$adminToken = "dev-admin-token"

Write-Host "=== TRACE-AI Demo Document Seeding ===" -ForegroundColor Cyan
Write-Host ""

# 1. Policy document ingestion (for Compliance scenario)
Write-Host "[1/3] Ingesting Policy document..." -ForegroundColor Yellow
$policyResponse = curl.exe -X POST "$baseUrl/api/v1/admin/knowledge-store/ingest" `
  -H "X-Admin-Token: $adminToken" `
  -F "store_type=policy" `
  -F "tags=security,password,compliance" `
  -F "files=@demo_docs/policy_security_password.txt"

Write-Host $policyResponse
Write-Host ""

# 2. Incident document ingestion (for RCA scenario)
Write-Host "[2/3] Ingesting Incident document..." -ForegroundColor Yellow
$incidentResponse = curl.exe -X POST "$baseUrl/api/v1/admin/knowledge-store/ingest" `
  -H "X-Admin-Token: $adminToken" `
  -F "store_type=incident" `
  -F "tags=redis,connection,error" `
  -F "files=@demo_docs/incident_redis_connection.txt"

Write-Host $incidentResponse
Write-Host ""

# 3. System document ingestion (for Workflow scenario)
Write-Host "[3/3] Ingesting System document..." -ForegroundColor Yellow
$systemResponse = curl.exe -X POST "$baseUrl/api/v1/admin/knowledge-store/ingest" `
  -H "X-Admin-Token: $adminToken" `
  -F "store_type=system" `
  -F "tags=deployment,procedure,production" `
  -F "files=@demo_docs/system_deployment_procedure.txt"

Write-Host $systemResponse
Write-Host ""

# Storage statistics
Write-Host "=== Storage Statistics ===" -ForegroundColor Cyan
Write-Host ""

Write-Host "[Policy] Fetching statistics..." -ForegroundColor Yellow
curl.exe -X GET "$baseUrl/api/v1/admin/knowledge-store/stats?store_type=policy" `
  -H "X-Admin-Token: $adminToken"

Write-Host ""

Write-Host "[Incident] Fetching statistics..." -ForegroundColor Yellow
curl.exe -X GET "$baseUrl/api/v1/admin/knowledge-store/stats?store_type=incident" `
  -H "X-Admin-Token: $adminToken"

Write-Host ""

Write-Host "[System] Fetching statistics..." -ForegroundColor Yellow
curl.exe -X GET "$baseUrl/api/v1/admin/knowledge-store/stats?store_type=system" `
  -H "X-Admin-Token: $adminToken"

Write-Host ""
Write-Host "=== Document Seeding Complete ===" -ForegroundColor Green
