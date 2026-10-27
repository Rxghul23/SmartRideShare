$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$env:JAVA_HOME = Join-Path $projectRoot '.tools\jdk-21.0.8+9'
$env:PYTHONPATH = Join-Path $projectRoot '.tools\python'
$env:TEMP = Join-Path $projectRoot 'tmp'
$env:TMP = $env:TEMP
$env:CATALINA_HOME = Join-Path $projectRoot '.tools\apache-tomcat-10.1.44'
$env:CATALINA_BASE = $env:CATALINA_HOME
$configPath = Join-Path $projectRoot '.local-config.json'
if (Test-Path -LiteralPath $configPath) {
 $localConfig = Get-Content -Raw -LiteralPath $configPath | ConvertFrom-Json
 $env:DB_URL = 'jdbc:mysql://127.0.0.1:3307/smartride?serverTimezone=Asia/Kolkata'
 $env:DB_USER = 'smartride'
 $env:DB_PASSWORD = $localConfig.dbPassword
 $env:ML_SERVICE_KEY = $localConfig.serviceKey
}
$env:ML_URL = 'http://127.0.0.1:5001'
$env:MODEL_PATH = Join-Path $projectRoot 'ml-service\models\matching.joblib'
