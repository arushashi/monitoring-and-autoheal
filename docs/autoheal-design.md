# Designing auto-healing that doesn't make things worse

Auto-healing removes 2 a.m. toil, but a careless automation can turn a small
fault into a large outage. Principles used in this repo:

1. **Only automate well-understood, low-risk fixes.** Restarting a stateless
   service: yes. Failing over a database: needs a human.
2. **Allow-list, never block-list.** Alerts map to explicit actions; everything
   else does nothing.
3. **Validate every input** that ends up in a command line. Alert labels are
   untrusted data.
4. **Rate-limit and cool down.** If a restart didn't help, doing it again every
   minute hides the real problem and can cause restart storms.
5. **Back off, then escalate.** Retry with exponential delay a few times, then
   page a human with the context of what was already tried.
6. **Dry-run first.** New automations run in log-only mode until their
   decisions have been reviewed.
7. **Audit everything.** Each decision (run, skip, reason) is logged as
   structured JSON and visible on the incident timeline.
8. **Keep a kill switch.** One flag or config toggle must disable all
   remediation instantly.
9. **Fix the cause afterwards.** Auto-healing buys time; each trigger should
   create or update a problem ticket so the root cause is removed.

## Flow

```
alert fires -> webhook -> allow-listed? -> valid labels? -> cooldown? -> run (or dry-run) -> audit log
                                                                  \-> still failing after N tries -> page on-call
```

## Measure it
- Number of automatic remediations per week (should fall as root causes are fixed)
- Success rate: alert resolved within 10 minutes after the action
- Escalations: cases the automation could not solve
