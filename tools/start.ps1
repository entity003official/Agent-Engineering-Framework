$ErrorActionPreference = 'Stop'
$launcher = Join-Path (Split-Path $PSScriptRoot -Parent) 'aef.py'
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw 'Python 3 is required. Nothing was installed.'
}
$aefProject = Read-Host 'Project folder'
$aefGoal = Read-Host 'Task goal'
if ([string]::IsNullOrWhiteSpace($aefProject) -or [string]::IsNullOrWhiteSpace($aefGoal)) {
    throw 'Project folder and task goal are required.'
}
& python -B $launcher init --project $aefProject --goal $aefGoal --platform both --dry-run
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
$aefApply = Read-Host 'Apply the changes above? [y/N]'
if ($aefApply -ne 'y') { exit 0 }
& python -B $launcher init --project $aefProject --goal $aefGoal --platform both
exit $LASTEXITCODE
