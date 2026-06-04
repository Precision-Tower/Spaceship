from UI.scripts.cli.commands.base import Command
from UI.scripts.cli.commands.git_commands import GitStatusCommand
from UI.scripts.cli.commands.patch_commands import (
    ApplyPatchCommand, 
    ClearDiffCommand, 
    ViewDiffCommand, 
    GrantReviewCommand
)
from UI.scripts.cli.commands.ai_commands import GeminiAnalyzeCommand, GeminiListModelsCommand
from UI.scripts.cli.commands.packet_commands import CreatePacketCommand, ListPacketsCommand
from UI.scripts.cli.commands.observation_commands import (
    ScanRepoCommand, 
    RuntimeStateCommand, 
    TestAllCommand,
    CaliObserveCommand
)
from UI.scripts.cli.commands.file_tools import ApplyCodeCommand, ReadFileCommand

# The registry remains the same, as it links the names to these classes
COMMAND_REGISTRY = {
    "git-status": GitStatusCommand,
    "apply-code": ApplyCodeCommand,
    "read-file": ReadFileCommand,
    "apply-patch": ApplyPatchCommand,
    "clear-latest-diff": ClearDiffCommand,
    "view-latest-diff": ViewDiffCommand,
    "grant-review": GrantReviewCommand,
    "gemini-analyze": GeminiAnalyzeCommand,
    "gemini-list-models": GeminiListModelsCommand,
    "create-packet": CreatePacketCommand,
    "list-packets": ListPacketsCommand,
    "scan-repo": ScanRepoCommand,
    "runtime-state": RuntimeStateCommand,
    "test-all": TestAllCommand,
    "cali-observe": CaliObserveCommand,
}

__all__ = ["COMMAND_REGISTRY", "Command"]
