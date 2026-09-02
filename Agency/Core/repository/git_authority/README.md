Git is CE-OS's historian and referee.

CE-OS shall not persist as current truth anything Git can authoritatively answer at query time.
CE-OS may persist immutable Git references and time-bounded Git observations as historical evidence.

Prohibited duplicate state:
- `current_branch`
- `current_head`
- `working_tree_clean`
- `repository_status`
- `changed_files`
- `current_diff`
- `commit_history`

Allowed references:
- repository-relative paths
- commit, tree, and blob OIDs
- baseline OIDs and hashes
- before and after hashes used for authorization and drift detection

Allowed evidence:
- the Git command invoked
- observation timestamp
- exit code
- stdout/stderr hash
- HEAD OID observed at execution time
- verification results

Live queries:
- current branch, HEAD, cleanliness, staged paths, unstaged paths, untracked paths, conflicts, diffs, merge bases, and object existence must be asked from Git when needed.

Authority ownership:
- mission and acceptance: Seth
- play direction and next decision: Gear
- ball possession: CE-OS
- route execution: Cali
- repository contents, history, status, branch topology, and object integrity: Git
