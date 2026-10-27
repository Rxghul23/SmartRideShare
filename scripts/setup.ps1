$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
New-Item -ItemType Directory -Force -Path "$projectRoot\tmp", "$projectRoot\.tools" | Out-Null
$env:TEMP = "$projectRoot\tmp"
$env:TMP = $env:TEMP
python "$PSScriptRoot\bootstrap_tools.py"
if ($LASTEXITCODE -ne 0) { throw 'Runtime download failed' }
python -m pip install --no-cache-dir --target "$projectRoot\.tools\python" -r "$projectRoot\ml-service\requirements.txt"
if ($LASTEXITCODE -ne 0) { throw 'Python dependency installation failed' }
. "$PSScriptRoot\env.ps1"
$mysqlBase = 'C:/Program Files/MySQL/MySQL Server 8.0'
if (!(Test-Path -LiteralPath "$mysqlBase/bin/mysqld.exe")) { throw 'Install MySQL Server 8.0 or update mysqlBase in this script.' }
$ini = @"
[mysqld]
basedir=$mysqlBase
datadir=$($projectRoot.Replace('\','/'))/.tools/mysql-data
port=3307
bind-address=127.0.0.1
mysqlx=0
innodb_buffer_pool_size=128M
log-error=$($projectRoot.Replace('\','/'))/tmp/mysql-error.log
default-time-zone=+05:30
"@
$ini | Set-Content -LiteralPath "$projectRoot\.tools\my.ini" -Encoding ascii
if (!(Test-Path -LiteralPath "$projectRoot\.tools\mysql-data")) {
 & "$mysqlBase/bin/mysqld.exe" "--defaults-file=$projectRoot\.tools\my.ini" --initialize-insecure
 if ($LASTEXITCODE -ne 0) { throw 'Project MySQL initialization failed' }
}
$server = "$env:CATALINA_HOME\conf\server.xml"
$serverText = Get-Content -Raw -LiteralPath $server
$serverText.Replace('<Connector port="8080"', '<Connector address="127.0.0.1" port="8080"') | Set-Content -LiteralPath $server
& "$PSScriptRoot\build.ps1"
& "$PSScriptRoot\start.ps1"
