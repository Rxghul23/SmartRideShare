. "$PSScriptRoot\env.ps1"
function Port-Open([int]$port) {
 $client = New-Object System.Net.Sockets.TcpClient
 try { $client.Connect('127.0.0.1', $port); return $true } catch { return $false } finally { $client.Dispose() }
}
if (!(Test-Path -LiteralPath "$projectRoot\.tools\mysql-data")) { throw 'Run scripts\setup.ps1 first.' }
if (!(Port-Open 3307)) {
 $mysqlProcess = Start-Process -FilePath 'C:\Program Files\MySQL\MySQL Server 8.0\bin\mysqld.exe' -ArgumentList "--defaults-file=$projectRoot\.tools\my.ini" -WindowStyle Hidden -PassThru
 $mysqlProcess.Id | Set-Content "$projectRoot\tmp\mysql.pid"
}
for ($attempt=0; $attempt -lt 30 -and !(Port-Open 3307); $attempt++) { Start-Sleep -Milliseconds 500 }
if (!(Port-Open 3307)) { throw 'MySQL did not start. See tmp\mysql-error.log.' }
if (!(Test-Path -LiteralPath "$projectRoot\.local-config.json")) { python "$PSScriptRoot\init_db.py"; if ($LASTEXITCODE -ne 0) { throw 'Database initialization failed' }; . "$PSScriptRoot\env.ps1" }
python "$PSScriptRoot\migrate.py"
if ($LASTEXITCODE -ne 0) { throw 'Database migration failed' }
if (!(Port-Open 5001)) {
 $pythonExe = (Get-Command python).Source
 $mlProcess = Start-Process -FilePath $pythonExe -ArgumentList "`"$projectRoot\ml-service\app.py`"" -WorkingDirectory $projectRoot -WindowStyle Hidden -RedirectStandardOutput "$projectRoot\tmp\ml-out.log" -RedirectStandardError "$projectRoot\tmp\ml-error.log" -PassThru
 $mlProcess.Id | Set-Content "$projectRoot\tmp\ml.pid"
}
if (!(Port-Open 8080)) {
 if (!(Test-Path -LiteralPath "$env:CATALINA_HOME\webapps\smartride.war")) { & "$PSScriptRoot\build.ps1" }
 $javaArgs = @('-Duser.timezone=Asia/Kolkata', "-Dcatalina.home=$env:CATALINA_HOME", "-Dcatalina.base=$env:CATALINA_BASE", "-Djava.io.tmpdir=$projectRoot\tmp", '-classpath', "$env:CATALINA_HOME\bin\bootstrap.jar;$env:CATALINA_HOME\bin\tomcat-juli.jar", 'org.apache.catalina.startup.Bootstrap', 'start')
 $tomcatProcess = Start-Process -FilePath "$env:JAVA_HOME\bin\java.exe" -ArgumentList $javaArgs -WorkingDirectory $projectRoot -WindowStyle Hidden -RedirectStandardOutput "$projectRoot\tmp\tomcat-out.log" -RedirectStandardError "$projectRoot\tmp\tomcat-error.log" -PassThru
 $tomcatProcess.Id | Set-Content "$projectRoot\tmp\tomcat.pid"
}
for ($attempt=0; $attempt -lt 60; $attempt++) {
 try { $response=Invoke-WebRequest 'http://127.0.0.1:8080/smartride/' -UseBasicParsing -TimeoutSec 5; if ($response.StatusCode -eq 200 -and (Port-Open 5001)) { Write-Host 'SmartRide is running: http://localhost:8080/smartride/'; Write-Host 'Demo sign-in details: LOCAL-LOGIN.txt'; exit 0 } } catch {}
 Start-Sleep -Milliseconds 500
}
throw 'Application startup incomplete. See tmp\tomcat-error.log and tmp\ml-error.log.'
