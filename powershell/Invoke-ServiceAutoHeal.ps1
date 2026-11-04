<#
.SYNOPSIS
  Restarts a Windows service if it is not running, with retries, back-off
  and an audit log. Supports -WhatIf.
.EXAMPLE
  .\Invoke-ServiceAutoHeal.ps1 -ServiceName Spooler -MaxAttempts 3 -WhatIf
#>
[CmdletBinding(SupportsShouldProcess)]
param(
    [Parameter(Mandatory)][string]$ServiceName,
    [int]$MaxAttempts = 3,
    [int]$InitialDelaySec = 5,
    [string]$LogPath = "$env:ProgramData\autoheal\autoheal.log"
)

function Write-Audit([string]$Message, [string]$Level = 'INFO') {
    $dir = Split-Path $LogPath
    if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
    $line = '{0:u} [{1}] {2} {3}' -f (Get-Date), $Level, $ServiceName, $Message
    Add-Content -Path $LogPath -Value $line
    Write-Verbose $line
}

$svc = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if (-not $svc) { Write-Audit 'service not found' 'ERROR'; exit 3 }
if ($svc.Status -eq 'Running') { Write-Audit 'already running, nothing to do'; exit 0 }
if ($svc.StartType -eq 'Disabled') { Write-Audit 'service is disabled on purpose, not restarting' 'WARN'; exit 4 }

$delay = $InitialDelaySec
for ($i = 1; $i -le $MaxAttempts; $i++) {
    if ($PSCmdlet.ShouldProcess($ServiceName, "Start service (attempt $i of $MaxAttempts)")) {
        try {
            Start-Service -Name $ServiceName -ErrorAction Stop
            $svc.WaitForStatus('Running', [TimeSpan]::FromSeconds(30))
            Write-Audit "recovered on attempt $i"
            exit 0
        } catch {
            Write-Audit "attempt $i failed: $($_.Exception.Message)" 'WARN'
        }
        Start-Sleep -Seconds $delay
        $delay *= 2                       # exponential back-off
        $svc.Refresh()
    } else {
        exit 0                            # -WhatIf
    }
}

Write-Audit "gave up after $MaxAttempts attempts: escalate to a human" 'ERROR'
exit 2
