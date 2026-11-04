<#
.SYNOPSIS
  Connects to each host over TLS and reports days until the certificate expires.
  Exit code 1 if any certificate is within -WarnDays (or unreachable).
.EXAMPLE
  .\Test-CertExpiry.ps1 -Hosts example.com,github.com -WarnDays 30
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory)][string[]]$Hosts,
    [int]$Port = 443,
    [int]$WarnDays = 30
)

function Get-RemoteCert([string]$HostName, [int]$Port) {
    $client = New-Object Net.Sockets.TcpClient
    try {
        $client.Connect($HostName, $Port)
        $callback = { param($s, $c, $ch, $e) $true }      # we only read the cert, trust is not the question here
        $ssl = New-Object Net.Security.SslStream($client.GetStream(), $false, $callback)
        $ssl.AuthenticateAsClient($HostName)
        return New-Object Security.Cryptography.X509Certificates.X509Certificate2($ssl.RemoteCertificate)
    } finally { $client.Close() }
}

$rows = foreach ($h in $Hosts) {
    try {
        $cert = Get-RemoteCert $h $Port
        $days = [math]::Floor(($cert.NotAfter - (Get-Date)).TotalDays)
        [pscustomobject]@{
            Host = $h; Expires = $cert.NotAfter.ToString('yyyy-MM-dd'); DaysLeft = $days
            Issuer = $cert.Issuer; Status = if ($days -le $WarnDays) { 'WARN' } else { 'OK' }
        }
    } catch {
        [pscustomobject]@{ Host = $h; Expires = ''; DaysLeft = $null; Issuer = $_.Exception.Message; Status = 'ERROR' }
    }
}

$rows | Sort-Object DaysLeft | Format-Table -AutoSize
if ($rows | Where-Object { $_.Status -ne 'OK' }) { exit 1 } else { exit 0 }
