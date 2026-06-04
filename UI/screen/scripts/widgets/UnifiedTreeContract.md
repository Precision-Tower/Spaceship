# UnifiedTreeComponent Contract

Status: contract only.
Authority: navigation/display discipline only.

## Purpose

Directory, Screens, and Commands should eventually share one tree-building contract so the UI does not drift into three subtly different navigation systems.

## Consumers

- Directory
- Screens
- Commands

## Target Node Shape

```yaml
TreeNode:
  label: string
  collapsed: bool
  children: list[TreeNode]
  action: optional string
  metadata: optional map
```

## Required Guarantees

```yaml
guarantees:
  tree_display_is_navigation_only: true
  selected_node_does_not_grant_authority: true
  collapsed_node_does_not_disable_authority: true
  visual_structure_is_not_governance: true
  directory_tree_is_not_filesystem_proof: true
```

## Future Migration Order

```yaml
migration:
  step_1: contract_doc_only
  step_2: add_helper_functions_unused
  step_3: migrate_directory_only
  step_4: migrate_screens_only
  step_5: migrate_commands_only
```

## Blocked

```yaml
blocked:
  - recursive_tree_refactor_bundle
  - hidden_tree_actions
  - filesystem_mutation_from_tree_click
  - authority_claims_from_navigation_state
```
