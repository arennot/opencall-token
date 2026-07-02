$SUPABASE_URL = "https://mbmzekzhgbngpvdibfea.supabase.co"
$SERVICE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1ibXpla3poZ2JuZ3B2ZGliZmVhIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4Mjg2OTQ2NCwiZXhwIjoyMDk4NDQ1NDY0fQ.A89_SQyRqmuw_F5Vvwm3gqhL-CaINP8aIp1oobQMIXE"
$appjs = Get-Content "C:\Users\arenn\Documents\Codex\2026-06-30\opencall-token\outputs\opencall-token\app.js" -Encoding UTF8 -Raw
$match = [regex]::Match($appjs, '(?s)const opportunities = (\[.+?\]);')
if (!$match.Success) { Write-Error "Not found"; exit 1 }
$json = $match.Groups[1].Value -replace ',\s*\]', ']' -replace 'undefined', 'null'
$items = $json | ConvertFrom-Json
Write-Host ("Found " + $items.Count + " items")
$headers = @{
  apikey = $SERVICE_KEY
  Authorization = "Bearer " + $SERVICE_KEY
  "Content-Type" = "application/json"
}
$i = 0; $s = 0
foreach ($opp in $items) {
  $body = @{
    title = $opp.title; type = $opp.type; organization = $opp.organization
    deadline = if ($opp.deadline) { $opp.deadline } else { $null }
    location = $opp.location; disciplines = $opp.disciplines
    funding = if ($opp.funding) { $opp.funding } else { $null }
    description = $opp.description; url = $opp.url
    source = $opp.source; posted_at = $opp.posted_at
    featured = if ($opp.featured) { $true } else { $false }
    is_local = $false; status = "published"
  } | ConvertTo-Json -Compress
  try {
    Invoke-RestMethod -Uri ($SUPABASE_URL + "/rest/v1/opportunities") -Method Post -Headers $headers -Body $body -ErrorAction Stop | Out-Null
    Write-Host ("  [OK] " + $opp.title)
    $i++
  } catch {
    Write-Host ("  [-] " + $opp.title + ": " + $_.Exception.Message.Substring(0, [Math]::Min(80, $_.Exception.Message.Length)))
    $s++
  }
}
Write-Host ("
Done! Inserted: " + $i + ", Skipped: " + $s)