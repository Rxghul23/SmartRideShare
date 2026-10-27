. "$PSScriptRoot\env.ps1"
foreach ($service in @('tomcat','ml')) {
 $pidFile=Join-Path $projectRoot "tmp\$service.pid"
 if (Test-Path -LiteralPath $pidFile) {
  $processId=[int](Get-Content -LiteralPath $pidFile)
  $processInfo=Get-CimInstance Win32_Process -Filter "ProcessId=$processId"
  if ($processInfo -and $processInfo.CommandLine -like "*$projectRoot*") { Stop-Process -Id $processId -ErrorAction SilentlyContinue; Write-Host "$service stopped" }
 }
}
python "$PSScriptRoot\stop_db.py"
