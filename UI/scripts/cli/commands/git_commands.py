import subprocess
from UI.scripts.cli.commands.base import Command

class GitStatusCommand(Command):
    """
    Handles git status checks using Python's built-in subprocess.
    No external git_tools.py required.
    """
    def run(self, args):
        # Access the root from our inherited resolver
        root = str(self.resolver.dashboard_root)
        
        try:
            # Run git status directly
            result = subprocess.run(
                ["git", "status", "--short"],
                cwd=root,
                capture_output=True,
                text=True,
                check=False
            )
            
            print("GIT_STATUS")
            print(f"root: {root}")
            
            if result.returncode != 0:
                print("status: git_error")
                print(result.stderr.strip())
                return
                
            status = "clean" if not result.stdout.strip() else "changes_present"
            print(f"status: {status}")
            print(result.stdout.strip() or "(no changes reported)")
            
        except FileNotFoundError:
            print("status: git_error")
            print("Error: 'git' command not found. Is git installed?")
        except Exception as e:
            print(f"status: execution_error")
            print(str(e))