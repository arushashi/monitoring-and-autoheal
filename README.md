# monitoring-and-autoheal

Scripts and design notes for **safe, alert-driven auto-healing** and basic health monitoring.
Generic examples; adapt names and thresholds to your environment.

| Path | What it does |
|---|---|
| `powershell/Invoke-ServiceAutoHeal.ps1` | Restarts a failed Windows service with retry, back-off and an audit log |
| `powershell/Test-CertExpiry.ps1` | Checks the TLS certificates of a list of endpoints and flags those expiring soon |
| `python/health_check.py` | HTTP probe with latency threshold and Nagios-style exit codes |
| `python/webhook_autoheal.py` | Receives Alertmanager-style webhooks and runs **allow-listed** remediation, with cooldowns and dry-run |
| `tests/` | Unit tests for the webhook decision logic |
| `docs/autoheal-design.md` | Principles for auto-healing that doesn't make incidents worse |

## Quick start

```powershell
# Dry run: shows what would happen
.\powershell\Invoke-ServiceAutoHeal.ps1 -ServiceName Spooler -WhatIf

# Check certificates
.\powershell\Test-CertExpiry.ps1 -Hosts example.com,github.com -WarnDays 30
```

```bash
python python/health_check.py https://example.com --max-ms 800
python python/webhook_autoheal.py --port 9000      # dry-run by default
python -m unittest discover tests
```

## License

MIT
