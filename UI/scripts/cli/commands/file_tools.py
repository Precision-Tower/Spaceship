# scripts/cli/commands/file_tools.py
from pathlib import Path
from UI.scripts.cli.commands.base import Command

class ApplyCodeCommand(Command):
    """
    Surgically updates a file with provided code content.
    Used by the Agent to apply architectural changes directly to the source.
    """
    def run(self, args):
        root = self.resolver.resolve_target_root(getattr(args, 'root', None))
        file_path = args.file
        code = args.code
        
        # Resolve target path
        target_path = (root / file_path).resolve()
        
        # Sanity check: Ensure we aren't writing outside of the project root
        if not str(target_path).startswith(str(root)):
            return self._report("denied", "reason: target path outside of project root")
            
        # Ensure the directory exists
        try:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Atomic Write
            target_path.write_text(code, encoding="utf-8")
            
            print("status: success")
            print(f"target: {file_path}")
            print(f"bytes_written: {len(code)}")
            
        except Exception as e:
            return self._report("apply_failed", str(e))

class ReadFileCommand(Command):
    """
    Allows the agent to read existing code to inform its next decision.
    """
    def run(self, args):
        root = self.resolver.resolve_target_root(getattr(args, 'root', None))
        target_path = (root / args.file).resolve()
        
        if not target_path.exists():
            return self._report("missing", f"file {args.file} not found")
            
        print("status: success")
        print(f"content:\n{target_path.read_text(encoding='utf-8', errors='replace')}")

