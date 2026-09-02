# Inspection Pass 001

- Mission: mission-3
- Timestamp: 2026-08-13T09:54:23.004106+00:00
- Inspection complete: True

## Files Inspected
- Agency/Core/work/missions/mission_runtime.py [primary] (110136 bytes, 2881 lines)

## Observations
- Read 1 files in inspection pass 1.
- Active queue by class: primary=1, secondary=0, evidence=0, ignored=0.
- Inspection pass 1 read primary file Agency/Core/work/missions/mission_runtime.py (2881 lines).

## Symbols
- Agency/Core/work/missions/mission_runtime.py:179 python_class MissionOperationError
- Agency/Core/work/missions/mission_runtime.py:180 python_function __init__
- Agency/Core/work/missions/mission_runtime.py:187 python_function _noop_refresh_pinboard
- Agency/Core/work/missions/mission_runtime.py:191 python_function _refresh_callback
- Agency/Core/work/missions/mission_runtime.py:195 python_function _emit_to
- Agency/Core/work/missions/mission_runtime.py:196 python_function emit
- Agency/Core/work/missions/mission_runtime.py:201 python_function _payload_from_text
- Agency/Core/work/missions/mission_runtime.py:215 python_function _operation_payload
- Agency/Core/work/missions/mission_runtime.py:226 python_function _run_emitting_operation
- Agency/Core/work/missions/mission_runtime.py:232 python_function _run_printing_operation
- Agency/Core/work/missions/mission_runtime.py:248 python_function _resolve_with_root
- Agency/Core/work/missions/mission_runtime.py:252 python_function _parse_model_json_object
- Agency/Core/work/missions/mission_runtime.py:272 python_function _as_string_list
- Agency/Core/work/missions/mission_runtime.py:290 python_function _run_command
- Agency/Core/work/missions/mission_runtime.py:295 python_function _git_status_lines
- Agency/Core/work/missions/mission_runtime.py:300 python_function _status_path
- Agency/Core/work/missions/mission_runtime.py:304 python_function _model_status
- Agency/Core/work/missions/mission_runtime.py:339 python_function _model_context_tokens
- Agency/Core/work/missions/mission_runtime.py:360 python_function _require_model_ready
- Agency/Core/work/missions/mission_runtime.py:379 python_function _call_model
- Agency/Core/work/missions/mission_runtime.py:392 python_function _mission_plan_dir
- Agency/Core/work/missions/mission_runtime.py:396 python_function _mission_plan_md_path
- Agency/Core/work/missions/mission_runtime.py:400 python_function _mission_proposal_dir
- Agency/Core/work/missions/mission_runtime.py:404 python_function _mission_proposal_md_path
- Agency/Core/work/missions/mission_runtime.py:408 python_function _mission_review_dir
- Agency/Core/work/missions/mission_runtime.py:412 python_function _load_plan
- Agency/Core/work/missions/mission_runtime.py:416 python_function _mission_review_decision_md_path
- Agency/Core/work/missions/mission_runtime.py:420 python_function _review_state_dependencies
- Agency/Core/work/missions/mission_runtime.py:435 python_function _load_proposal
- Agency/Core/work/missions/mission_runtime.py:439 python_function _load_review_inputs
- Agency/Core/work/missions/mission_runtime.py:443 python_function _update_state_after_review
- Agency/Core/work/missions/mission_runtime.py:447 python_function _review_failure_factory
- Agency/Core/work/missions/mission_runtime.py:448 python_function review_failure
- Agency/Core/work/missions/mission_runtime.py:453 python_function _planning_dependencies
- Agency/Core/work/missions/mission_runtime.py:489 python_function _proposal_dependencies
- Agency/Core/work/missions/mission_runtime.py:520 python_function _review_execution_dependencies
- Agency/Core/work/missions/mission_runtime.py:546 python_function _implementation_execution_dependencies
- Agency/Core/work/missions/mission_runtime.py:584 python_function _verification_execution_dependencies
- Agency/Core/work/missions/mission_runtime.py:624 python_function _missions_root
- Agency/Core/work/missions/mission_runtime.py:628 python_function _now
- Agency/Core/work/missions/mission_runtime.py:632 python_function _stable
- Agency/Core/work/missions/mission_runtime.py:636 python_function _load_json
- Agency/Core/work/missions/mission_runtime.py:646 python_function _atomic_json
- Agency/Core/work/missions/mission_runtime.py:653 python_function _atomic_text
- Agency/Core/work/missions/mission_runtime.py:660 python_function _is_relative_to
- Agency/Core/work/missions/mission_runtime.py:668 python_function agency_blocks_dependent_operations
- Agency/Core/work/missions/mission_runtime.py:687 python_function validate_engineering_scopes
- Agency/Core/work/missions/mission_runtime.py:746 python_function _mission_number_from_name
- Agency/Core/work/missions/mission_runtime.py:754 python_function _next_mission_number
- Agency/Core/work/missions/mission_runtime.py:767 python_function mission_id
- Agency/Core/work/missions/mission_runtime.py:? truncated symbol_limit_reached

## Dependencies
- Agency/Core/work/missions/mission_runtime.py:1 python_from __future__:annotations
- Agency/Core/work/missions/mission_runtime.py:3 python_import argparse
- Agency/Core/work/missions/mission_runtime.py:4 python_import contextlib
- Agency/Core/work/missions/mission_runtime.py:5 python_import io
- Agency/Core/work/missions/mission_runtime.py:6 python_import json
- Agency/Core/work/missions/mission_runtime.py:7 python_import os
- Agency/Core/work/missions/mission_runtime.py:8 python_import re
- Agency/Core/work/missions/mission_runtime.py:9 python_import subprocess
- Agency/Core/work/missions/mission_runtime.py:10 python_import sys
- Agency/Core/work/missions/mission_runtime.py:11 python_import time
- Agency/Core/work/missions/mission_runtime.py:12 python_from datetime:datetime, timezone
- Agency/Core/work/missions/mission_runtime.py:13 python_from pathlib:Path
- Agency/Core/work/missions/mission_runtime.py:14 python_from typing:Any, Callable
- Agency/Core/work/missions/mission_runtime.py:16 python_from Agency.Core.work.planning:mission_planning as _mission_planning
- Agency/Core/work/missions/mission_runtime.py:17 python_from Agency.Core.work.planning:proposal_generation as _proposal_generation
- Agency/Core/work/missions/mission_runtime.py:18 python_from Agency.Core.work.missions.pipeline.review.execution:(
- Agency/Core/work/missions/mission_runtime.py:22 python_from Agency.Core.runtime.commands:mission_command
- Agency/Core/work/missions/mission_runtime.py:23 python_from Agency.Core.work.missions.pipeline.review.helpers:(
- Agency/Core/work/missions/mission_runtime.py:28 python_from Agency.Core.work.missions.pipeline.review.state:(
- Agency/Core/work/missions/mission_runtime.py:37 python_from Agency.Core.work.missions.pipeline.implementation:execution as _implementation_execution
- Agency/Core/work/missions/mission_runtime.py:38 python_from Agency.Core.work.missions.pipeline.verification:execution as _verification_execution
- Agency/Core/work/missions/mission_runtime.py:39 python_from Agency.Core.runtime.resourcefulness:(
- Agency/Core/work/missions/mission_runtime.py:43 python_from Agency.Core.runtime.runtime_config:effective_model_context_tokens
- Agency/Core/work/missions/mission_runtime.py:45 python_from Agency.Core.repository.inspection.analysis:(
- Agency/Core/work/missions/mission_runtime.py:50 python_from Agency.Core.repository.inspection.context:(
- Agency/Core/work/missions/mission_runtime.py:54 python_from Agency.Core.repository.inspection.coverage:(
- Agency/Core/work/missions/mission_runtime.py:59 python_from Agency.Core.foundation.paths:(
- Agency/Core/work/missions/mission_runtime.py:306 python_from Agency.Core.runtime:model_server_manager
- Agency/Core/work/missions/mission_runtime.py:385 python_from Agency.Core.runtime:model_service

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
