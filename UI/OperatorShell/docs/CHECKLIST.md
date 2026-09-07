# OperatorShell Checklist

## Proven baseline

- [x] Canonical mission source identified: `UI/OperatorShell/MOBILE_IDE_CHECKLIST.md`.
- [x] Android build/install loop completed for the read-only Files -> Editor slice.
- [x] CE-OS API service reported running on Pixel.
- [x] Live API root listing returned repo-relative entries.
- [x] Live API read returned real `UI/OperatorShell/Main.gd` content.
- [x] Focused filesystem tests cover root and nested listing, directories-first/case-insensitive sorting, text reads, traversal rejection, symlink escape rejection, missing paths, wrong entry kinds, binary rejection, and `~` normalization.
- [x] Existing OperatorShell source-contract suite passed.

## Read-only Files -> Editor slice

- [x] Files root and directory navigation request `/v1/fs/list` through `HTTPRequest`.
- [x] File selection requests `/v1/fs/read` and loads returned UTF-8 content into `TextEdit`.
- [x] UI state stores repo-relative virtual paths.
- [x] `.git` is hidden by the Files UI.
- [x] Editor save is disabled; write support is not part of this slice.

## Runtime observation

- [ ] Pixel visual/control-server observation remains blocked by the existing Android launch state: the launcher activity stays topmost and no OperatorShell control server becomes reachable after clean close/launch. The API and APK build/install are independently proven.

## Next milestone

- [ ] Resolve the Android launcher/runtime observation blocker.
- [ ] Add runtime UI proof of directory navigation and real editor content.
- [ ] Decide and implement authenticated or otherwise bounded write semantics before enabling save.
- [ ] Add API-level HTTP integration tests in addition to helper-level behavior tests.
