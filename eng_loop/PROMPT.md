Read AGENT_PROCESS.md; it governs this session. This session is ONE outer-loop
iteration. Work sequentially through these steps and stop where instructed.

0. Billing check. Run:
   env | grep -iE 'ANTHROPIC_(API_KEY|AUTH_TOKEN|BASE_URL)|CLAUDE_CODE_USE_(BEDROCK|VERTEX)'
   Any match → print "BILLING-ROUTE VIOLATION: <variable>", do no other work, STOP.

1. Run ./verify.sh. If it exits 0 → print "DONE", STOP.

2. Select exactly one issue: the highest-priority open `agent-ready` issue
   whose dependencies are closed, skipping `verified` and `blocked`. If none
   is selectable → print "NO ELIGIBLE ISSUES" with the reason, STOP.

3. Run one /issue-loop cycle for that issue only:
   /issue-triage → (spec path if routed; park → comment why and STOP) →
   inner build loop → /code-verifier must APPROVE → merge →
   /deploy → /post-deploy-verify for surface-changing issues.
   Gates pass only by exit code or fresh-eyes subagent verdict — never by
   your own assessment.

4. On green: comment the evidence on the issue, add `verified`, close it.
   On red: iterate. On the 3rd consecutive failed verify cycle, apply the
   circuit breaker — revert main to green, post logs to the issue, label it
   `blocked` — then STOP.

5. Before stopping, write anything the next iteration needs to the issue or
   TASKS.md. Then STOP. Do not begin a second issue.
