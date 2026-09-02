from Agency.Core.interfaces.cli.commands.base import Command
from Agency.Core.interfaces.cli.commands.git_commands import GitStatusCommand
from Agency.Core.interfaces.cli.commands.patch_commands import (
    ApplyPatchCommand, 
    ClearDiffCommand, 
    ProposeDiffCommand,
    ViewDiffCommand, 
    GrantReviewCommand
)
from Agency.Core.interfaces.cli.commands.ai_commands import GeminiAnalyzeCommand, GeminiListModelsCommand
from Agency.Core.interfaces.cli.commands.packet_commands import CreatePacketCommand, ListPacketsCommand
from Agency.Core.interfaces.cli.commands.observation_commands import (
    ScanRepoCommand, 
    RuntimeStateCommand, 
    TestAllCommand,
    CaliObserveCommand
)
from Agency.Core.interfaces.cli.commands.file_tools import ApplyCodeCommand, ReadFileCommand
from Agency.Core.interfaces.cli.commands.agent_commands import ListAgentsCommand
from Agency.Core.interfaces.cli.commands.navigation_commands import RefsCommand, TreeCommand
from Agency.Core.foundation.shared_bridge import PathResolver

_RESOLVER = PathResolver()

git_status = GitStatusCommand(_RESOLVER)
apply_patch = ApplyPatchCommand(_RESOLVER)
clear_latest_diff = ClearDiffCommand(_RESOLVER)
view_latest_diff = ViewDiffCommand(_RESOLVER)
grant_review = GrantReviewCommand(_RESOLVER)
propose_diff = ProposeDiffCommand(_RESOLVER)
propose_directory_diff = ProposeDiffCommand(_RESOLVER)

gemini_analyze = GeminiAnalyzeCommand(_RESOLVER)
gemini_list_models = GeminiListModelsCommand(_RESOLVER)

create_packet = CreatePacketCommand(_RESOLVER)
list_packets = ListPacketsCommand(_RESOLVER)

scan_repo = ScanRepoCommand(_RESOLVER)
runtime_state = RuntimeStateCommand(_RESOLVER)
test_all = TestAllCommand(_RESOLVER)
cali_observe_directory = CaliObserveCommand(_RESOLVER)

# temporary compatibility aliases
grant_review_latest_diff = GrantReviewCommand(_RESOLVER)
list_agents = ListAgentsCommand(_RESOLVER)
apply_code = ApplyCodeCommand(_RESOLVER)
read_file = ReadFileCommand(_RESOLVER)
refs = RefsCommand(_RESOLVER)
tree = TreeCommand(_RESOLVER)


__all__ = [
    "Command",
    "git_status",
    "apply_patch",
    "clear_latest_diff",
    "view_latest_diff",
    "grant_review",
    "grant_review_latest_diff",
    "gemini_analyze",
    "gemini_list_models",
    "create_packet",
    "list_packets",
    "scan_repo",
    "runtime_state",
    "test_all",
    "cali_observe_directory",
    "propose_diff",
    "propose_directory_diff",
    "list_agents",
    "apply_code",
    "read_file",
    "refs",
    "tree",
]

