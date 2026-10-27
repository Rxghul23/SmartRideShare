param([switch]$SkipTests)
. "$PSScriptRoot\env.ps1"
Push-Location $projectRoot
try {
 $maven = Join-Path $projectRoot '.tools\apache-maven-3.9.11\bin\mvn.cmd'
 $buildArgs = @('-B', "-Dmaven.repo.local=$projectRoot\.tools\m2", 'package')
 if ($SkipTests) { $buildArgs += '-DskipTests' }
 & $maven @buildArgs
 if ($LASTEXITCODE -ne 0) { throw 'Java build failed' }
 Copy-Item -LiteralPath "$projectRoot\target\smartride.war" -Destination "$env:CATALINA_HOME\webapps\smartride.war" -Force
} finally { Pop-Location }
