from Agency.Core.interfaces.cli.commands.base import Command
from Agency.Core.repository.git_authority import GitAuthorityError, get_status, repository_ref

class GitStatusCommand(Command):
    """
    Handles git status checks through the Git Authority Boundary.
    """
    def run(self, args):
        try:
            repository = repository_ref(self.resolver.dashboard_root)
            status_view = get_status(repository)
            print("GIT_STATUS")
            print(f"root: {repository.root_path}")
            print(f"head: {status_view.head_oid}")
            print(f"branch: {status_view.branch or '<detached>'}")
            print(f"detached: {status_view.detached}")
            print(f"status: {'clean' if status_view.clean else 'changes_present'}")
            print("staged:")
            for path in status_view.staged_paths:
                print(f"  - {path}")
            print("unstaged:")
            for path in status_view.unstaged_paths:
                print(f"  - {path}")
            print("untracked:")
            for path in status_view.untracked_paths:
                print(f"  - {path}")
        except GitAuthorityError as exc:
            print("status: git_error")
            print(f"{exc.code}: {exc.message}")
        except Exception as e:
            print(f"status: execution_error")
            print(str(e))



