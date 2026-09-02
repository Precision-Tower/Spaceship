# Inspection Pass 001

- Mission: mission-4
- Timestamp: 2026-08-13T10:17:22.131911+00:00
- Inspection complete: True

## Files Inspected
- Agency/Core/work/missions/mission_runtime.py [primary] (121969 bytes, 3188 lines)

## Observations
- Read 1 files in inspection pass 1.
- Active queue by class: primary=1, secondary=0, evidence=0, ignored=0.
- Inspection pass 1 read primary file Agency/Core/work/missions/mission_runtime.py (3188 lines).

## Symbols
- Agency/Core/work/missions/mission_runtime.py:184 python_class MissionOperationError
- Agency/Core/work/missions/mission_runtime.py:185 python_function __init__
- Agency/Core/work/missions/mission_runtime.py:192 python_function _noop_refresh_pinboard
- Agency/Core/work/missions/mission_runtime.py:196 python_function _refresh_callback
- Agency/Core/work/missions/mission_runtime.py:200 python_function _emit_to
- Agency/Core/work/missions/mission_runtime.py:201 python_function emit
- Agency/Core/work/missions/mission_runtime.py:206 python_function _payload_from_text
- Agency/Core/work/missions/mission_runtime.py:220 python_function _operation_payload
- Agency/Core/work/missions/mission_runtime.py:231 python_function _run_emitting_operation
- Agency/Core/work/missions/mission_runtime.py:237 python_function _run_printing_operation
- Agency/Core/work/missions/mission_runtime.py:253 python_function _resolve_with_root
- Agency/Core/work/missions/mission_runtime.py:257 python_function _parse_model_json_object
- Agency/Core/work/missions/mission_runtime.py:277 python_function _as_string_list
- Agency/Core/work/missions/mission_runtime.py:295 python_function _run_command
- Agency/Core/work/missions/mission_runtime.py:300 python_function _git_status_lines
- Agency/Core/work/missions/mission_runtime.py:305 python_function _status_path
- Agency/Core/work/missions/mission_runtime.py:309 python_function _model_status
- Agency/Core/work/missions/mission_runtime.py:344 python_function _model_context_tokens
- Agency/Core/work/missions/mission_runtime.py:365 python_function _require_model_ready
- Agency/Core/work/missions/mission_runtime.py:384 python_function _call_model
- Agency/Core/work/missions/mission_runtime.py:397 python_function _mission_plan_dir
- Agency/Core/work/missions/mission_runtime.py:401 python_function _mission_plan_md_path
- Agency/Core/work/missions/mission_runtime.py:405 python_function _mission_proposal_dir
- Agency/Core/work/missions/mission_runtime.py:409 python_function _mission_proposal_md_path
- Agency/Core/work/missions/mission_runtime.py:413 python_function _mission_review_dir
- Agency/Core/work/missions/mission_runtime.py:417 python_function _load_plan
- Agency/Core/work/missions/mission_runtime.py:421 python_function _mission_review_decision_md_path
- Agency/Core/work/missions/mission_runtime.py:425 python_function _review_state_dependencies
- Agency/Core/work/missions/mission_runtime.py:440 python_function _load_proposal
- Agency/Core/work/missions/mission_runtime.py:444 python_function _load_review_inputs
- Agency/Core/work/missions/mission_runtime.py:448 python_function _update_state_after_review
- Agency/Core/work/missions/mission_runtime.py:452 python_function _review_failure_factory
- Agency/Core/work/missions/mission_runtime.py:453 python_function review_failure
- Agency/Core/work/missions/mission_runtime.py:458 python_function _planning_dependencies
- Agency/Core/work/missions/mission_runtime.py:495 python_function _proposal_dependencies
- Agency/Core/work/missions/mission_runtime.py:526 python_function _review_execution_dependencies
- Agency/Core/work/missions/mission_runtime.py:552 python_function _implementation_execution_dependencies
- Agency/Core/work/missions/mission_runtime.py:590 python_function _verification_execution_dependencies
- Agency/Core/work/missions/mission_runtime.py:630 python_function _missions_root
- Agency/Core/work/missions/mission_runtime.py:634 python_function _now
- Agency/Core/work/missions/mission_runtime.py:638 python_function _stable
- Agency/Core/work/missions/mission_runtime.py:642 python_function _load_json
- Agency/Core/work/missions/mission_runtime.py:652 python_function _atomic_json
- Agency/Core/work/missions/mission_runtime.py:659 python_function _atomic_text
- Agency/Core/work/missions/mission_runtime.py:666 python_function _is_relative_to
- Agency/Core/work/missions/mission_runtime.py:674 python_function agency_blocks_dependent_operations
- Agency/Core/work/missions/mission_runtime.py:693 python_function validate_engineering_scopes
- Agency/Core/work/missions/mission_runtime.py:752 python_function _mission_number_from_name
- Agency/Core/work/missions/mission_runtime.py:760 python_function _next_mission_number
- Agency/Core/work/missions/mission_runtime.py:773 python_function mission_id
- Agency/Core/work/missions/mission_runtime.py:? truncated symbol_limit_reached

## Dependencies
- Agency/Core/work/missions/mission_runtime.py:1 python_from __future__:annotations
- Agency/Core/work/missions/mission_runtime.py:3 python_import argparse
- Agency/Core/work/missions/mission_runtime.py:4 python_import contextlib
- Agency/Core/work/missions/mission_runtime.py:5 python_import io
- Agency/Core/work/missions/mission_runtime.py:6 python_import json
- Agency/Core/work/missions/mission_runtime.py:7 python_import os
- Agency/Core/work/missions/mission_runtime.py:8 python_import re
- Agency/Core/work/missions/mission_runtime.py:9 python_import shlex
- Agency/Core/work/missions/mission_runtime.py:10 python_import subprocess
- Agency/Core/work/missions/mission_runtime.py:11 python_import sys
- Agency/Core/work/missions/mission_runtime.py:12 python_import time
- Agency/Core/work/missions/mission_runtime.py:13 python_from datetime:datetime, timezone
- Agency/Core/work/missions/mission_runtime.py:14 python_from pathlib:Path
- Agency/Core/work/missions/mission_runtime.py:15 python_from typing:Any, Callable
- Agency/Core/work/missions/mission_runtime.py:17 python_from Agency.Core.work.planning:mission_planning as _mission_planning
- Agency/Core/work/missions/mission_runtime.py:18 python_from Agency.Core.work.planning:proposal_generation as _proposal_generation
- Agency/Core/work/missions/mission_runtime.py:19 python_from Agency.Core.work.missions.pipeline.review.execution:(
- Agency/Core/work/missions/mission_runtime.py:23 python_from Agency.Core.runtime.commands:mission_command
- Agency/Core/work/missions/mission_runtime.py:24 python_from Agency.Core.work.missions.pipeline.review.helpers:(
- Agency/Core/work/missions/mission_runtime.py:29 python_from Agency.Core.work.missions.pipeline.review.state:(
- Agency/Core/work/missions/mission_runtime.py:38 python_from Agency.Core.work.missions.pipeline.implementation:execution as _implementation_execution
- Agency/Core/work/missions/mission_runtime.py:39 python_from Agency.Core.work.missions.pipeline.verification:execution as _verification_execution
- Agency/Core/work/missions/mission_runtime.py:40 python_from Agency.Core.runtime.resourcefulness:(
- Agency/Core/work/missions/mission_runtime.py:44 python_from Agency.Core.runtime.runtime_config:effective_model_context_tokens
- Agency/Core/work/missions/mission_runtime.py:46 python_from Agency.Core.repository.inspection.analysis:(
- Agency/Core/work/missions/mission_runtime.py:51 python_from Agency.Core.repository.inspection.context:(
- Agency/Core/work/missions/mission_runtime.py:55 python_from Agency.Core.repository.inspection.coverage:(
- Agency/Core/work/missions/mission_runtime.py:60 python_from Agency.Core.foundation.paths:(
- Agency/Core/work/missions/mission_runtime.py:311 python_from Agency.Core.runtime:model_server_manager
- Agency/Core/work/missions/mission_runtime.py:390 python_from Agency.Core.runtime:model_service

## Skipped
- none

## Coverage
```json
{
  "route_ownership": "partial",
  "workspace_host": "partial",
  "workbench_root": "partial",
  "creation_lifecycle": "partial",
  "cleanup_lifecycle": "partial",
  "expected_modified_files": "partial",
  "verification_surfaces": "partial"
}
```

## Unresolved
- none

## Next Files
- none
