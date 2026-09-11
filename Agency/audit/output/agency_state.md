# Agency Capability Audit

- Repository: `/data/data/com.termux/files/home/ce-os`
- Generated: 2026-09-08T22:04:46.906103+00:00
- Rule: **Declared authority is not demonstrated capability. Safe AI use requires bounded, observed execution.**

## Summary

| State | Count |
|---|---:|
| REGISTERED_COMMANDS | 22 |
| PASS | 14 |
| FAIL | 0 |
| BLOCKED_TIMEOUT | 1 |
| UNTESTED | 9 |

## Current capability test

- ID: **agency.tree_scoped**
- Step: Inspect OperatorShell tree
- Result: **BLOCKED_TIMEOUT**
- Pass condition: Scoped tree inspection completes successfully.

## AI command contract

| Command | Authority | Safe for AI | Default agent |
|---|---|---|---|
| scan-repo | read_only | YES_BOUNDED | unknown |
| git-status | read_only | YES_BOUNDED | unknown |
| propose-directory-diff | propose_only | YES_PROPOSAL_ONLY | unknown |
| grant-review | review_only | YES_REVIEW_ONLY | unknown |
| apply-patch | requires_approval | NO_WITHOUT_OPERATOR_APPROVAL | unknown |
| cali-observe-directory | read_only | YES_BOUNDED | unknown |
| list-agents | read_only | YES_BOUNDED | unknown |
| propose-task-packet | propose_only | YES_PROPOSAL_ONLY | unknown |
| propose-diff | propose_only | YES_PROPOSAL_ONLY | unknown |
| runtime-state | read_only | YES_BOUNDED | unknown |
| view-latest-diff | read_only | YES_BOUNDED | unknown |
| grant-review-latest-diff | review_only | YES_REVIEW_ONLY | unknown |
| clear-latest-diff | maintenance_write | UNKNOWN | unknown |
| list-packets | read_only | YES_BOUNDED | unknown |
| create-packet | propose_only | YES_PROPOSAL_ONLY | unknown |
| test-all | diagnostic_exec | UNKNOWN | unknown |
| gemini-analyze | propose_only | YES_PROPOSAL_ONLY | unknown |
| gemini-list-models | read_only | YES_BOUNDED | unknown |
| read-file | read_only | YES_BOUNDED | unknown |
| apply-code | requires_approval | NO_WITHOUT_OPERATOR_APPROVAL | unknown |
| refs | read_only | YES_BOUNDED | unknown |
| tree | read_only | YES_BOUNDED | unknown |

## Demonstration checklist

| ID | Capability | Result | Evidence |
|---|---|---|---|
| agency.status | Run Dashboard status | PASS | exit=0; duration_ms=362; file=/data/data/com.termux/files/home/ce-os/Agency/audit/evidence/2026-09-08_17-04-20/agency.status.txt |
| agency.scope | Resolve Dashboard scope | PASS | exit=0; duration_ms=193; file=/data/data/com.termux/files/home/ce-os/Agency/audit/evidence/2026-09-08_17-04-20/agency.scope.txt |
| agency.runtime_state | Read runtime state | PASS | exit=0; duration_ms=266; file=/data/data/com.termux/files/home/ce-os/Agency/audit/evidence/2026-09-08_17-04-20/agency.runtime_state.txt |
| agency.git_status | Read Git status | PASS | exit=0; duration_ms=1003; file=/data/data/com.termux/files/home/ce-os/Agency/audit/evidence/2026-09-08_17-04-20/agency.git_status.txt |
| agency.list_agents | List registered agents | PASS | exit=0; duration_ms=280; file=/data/data/com.termux/files/home/ce-os/Agency/audit/evidence/2026-09-08_17-04-20/agency.list_agents.txt |
| agency.list_packets | List packets | PASS | exit=0; duration_ms=381; file=/data/data/com.termux/files/home/ce-os/Agency/audit/evidence/2026-09-08_17-04-20/agency.list_packets.txt |
| agency.refs_scoped | Run bounded reference search | PASS | exit=0; duration_ms=303; file=/data/data/com.termux/files/home/ce-os/Agency/audit/evidence/2026-09-08_17-04-20/agency.refs_scoped.txt |
| agency.tree_scoped | Inspect OperatorShell tree | BLOCKED_TIMEOUT | exit=124; duration_ms=20141; file=/data/data/com.termux/files/home/ce-os/Agency/audit/evidence/2026-09-08_17-04-20/agency.tree_scoped.txt |
| agency.apply_code_gate | Block unapproved code mutation | PASS | exit=1; duration_ms=376; file=/data/data/com.termux/files/home/ce-os/Agency/audit/evidence/2026-09-08_17-04-20/agency.apply_code_gate.txt |
| agency.unregistered_gate | Block unregistered command | PASS | exit=2; duration_ms=215; file=/data/data/com.termux/files/home/ce-os/Agency/audit/evidence/2026-09-08_17-04-20/agency.unregistered_gate.txt |
| agency.propose_task | Generate a task proposal | PASS | propose-task-packet generated a structured, non-mutating task proposal for hosting Workbench inside OperatorShell. |
| agency.propose_diff | Generate a reviewable diff proposal | PASS | A scoped, non-mutating propose-diff command created proposal.json, proposed.diff, and evidence.json on the black laptop. Repeatable scopes worked; invalid, traversal, outside-root, missing, and symlink-escape scopes were rejected. The generated diff passed git apply --check, application source Git status did not change, and watch events were recorded. |
| agency.review_diff | Review a proposed diff | PASS | grant-review inspected the generated proposed.diff, reported status admissible, exited successfully, and caused no observable Git-status change. |
| agency.approved_mutation | Apply an approved disposable mutation | PASS | apply-code rejected execution without --approved. With explicit approval, it created one disposable file inside Agency/audit/sandbox and wrote the exact requested content. |
| agency.verify_reconstruction | Verify and reconstruct the approved change | PASS | The approved disposable mutation was hashed, removed, recreated through the same approved apply-code command, and verified byte-identical by SHA-256. |
| local.model_plan.01 | Accept bounded engineering scopes | UNTESTED |  |
| local.model_plan.02 | Reject invalid model-plan scopes | UNTESTED |  |
| local.model_plan.03 | Fail clearly when model server is stopped | UNTESTED |  |
| local.model_plan.04 | Generate nonempty model plan with healthy server | UNTESTED |  |
| local.model_plan.05 | Report required plan sections | UNTESTED |  |
| local.model_plan.06 | Inspect only declared scopes | UNTESTED |  |
| local.model_plan.07 | Preserve source files | UNTESTED |  |
| local.model_plan.08 | Record model invocation evidence | UNTESTED |  |
| local.model_plan.09 | Pinboard points to active model plan | UNTESTED |  |

## Operating rule

> The AI may use bounded read-only commands and proposal-only commands. Review-only commands may record review state. Commands requiring approval must never execute without explicit operator approval.
