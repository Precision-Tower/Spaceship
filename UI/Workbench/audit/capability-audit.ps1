param(
    [string]$RepoRoot = "",
    [switch]$RunSmokeTests
)

$ErrorActionPreference = "Stop"

$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

if ([string]::IsNullOrWhiteSpace($RepoRoot)) {
    $RepoRoot = (Resolve-Path (Join-Path $ScriptRoot "..\..\..\..")).Path
} else {
    $RepoRoot = (Resolve-Path $RepoRoot).Path
}

$OutputRoot = Join-Path $ScriptRoot "output"
$EvidenceRoot = Join-Path $ScriptRoot "evidence"
$ObservationsPath = Join-Path $ScriptRoot "observations.json"

New-Item -ItemType Directory -Force -Path $OutputRoot | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $EvidenceRoot "screenshots") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $EvidenceRoot "logs") | Out-Null

function New-Check {
    param(
        [string]$Id,
        [string]$Category,
        [string]$Capability,
        [string]$Level,
        [string]$Status,
        [string]$Evidence,
        [string]$NextProof
    )

    [pscustomobject]@{
        id = $Id
        category = $Category
        capability = $Capability
        evidence_level = $Level
        status = $Status
        evidence = $Evidence
        next_proof = $NextProof
    }
}

function Test-AnyPath {
    param([string[]]$RelativePaths)

    $hits = @()

    foreach ($relative in $RelativePaths) {
        if (Test-Path (Join-Path $RepoRoot $relative)) {
            $hits += $relative
        }
    }

    return $hits
}

function Add-PathCheck {
    param(
        [System.Collections.Generic.List[object]]$Checks,
        [string]$Id,
        [string]$Category,
        [string]$Capability,
        [string[]]$Paths,
        [string]$NextProof
    )

    $hits = Test-AnyPath $Paths

    if ($hits.Count -gt 0) {
        $Checks.Add((New-Check $Id $Category $Capability "PRESENT" "FOUND" ($hits -join ", ") $NextProof))
    } else {
        $Checks.Add((New-Check $Id $Category $Capability "NONE" "NOT FOUND" ("Checked: " + ($Paths -join ", ")) $NextProof))
    }
}

function Find-Text {
    param(
        [string[]]$Patterns,
        [string[]]$Extensions = @("*.gd"),
        [string]$SearchRoot = $RepoRoot
    )

    if (-not (Test-Path $SearchRoot)) {
        return @()
    }

    $files = @()

    foreach ($ext in $Extensions) {
        $files += Get-ChildItem -Path $SearchRoot -Recurse -File -Filter $ext -ErrorAction SilentlyContinue |
            Where-Object {
                $_.FullName -notmatch '[\\/](\.git|\.godot|archive|__pycache__|node_modules|_zip_test)[\\/]'
            }
    }

    $results = @()

    foreach ($pattern in $Patterns) {
        $found = $files | Select-String -Pattern $pattern -SimpleMatch -ErrorAction SilentlyContinue

        foreach ($item in $found) {
            $relative = $item.Path.Substring($RepoRoot.Length).TrimStart('\', '/')
            $results += ($relative + ":" + $item.LineNumber)
        }
    }

    return $results | Sort-Object -Unique
}

function Ensure-ObservationsFile {
    if (-not (Test-Path $ObservationsPath)) {
        [ordered]@{
            schema_version = 1
            updated_at = (Get-Date).ToString("o")
            observations = [ordered]@{}
        } |
            ConvertTo-Json -Depth 8 |
            Set-Content -Path $ObservationsPath -Encoding UTF8
    }
}

function Get-ObservationRecord {
    param(
        [object]$ObservationDocument,
        [string]$Id
    )

    $property = $ObservationDocument.observations.PSObject.Properties[$Id]

    if ($null -eq $property) {
        return [pscustomobject]@{
            result = "UNTESTED"
            evidence = ""
            unresolved = @()
        }
    }

    $record = $property.Value
    $evidenceText = @(
        $record.evidence | ForEach-Object {
            if ($_.observation) { $_.observation }
            elseif ($_ -is [string]) { $_ }
        }
    ) -join "; "

    [pscustomobject]@{
        result = if ($record.result) { $record.result } else { "UNTESTED" }
        evidence = $evidenceText
        unresolved = @($record.unresolved)
    }
}

Write-Host "Auditing repository: $RepoRoot" -ForegroundColor Cyan

$checks = [System.Collections.Generic.List[object]]::new()

Add-PathCheck $checks "repo.run_py" "Runtime" "Root runtime entrypoint exists" `
    @("run.py", "Dashboard/run.py") `
    "Run the entrypoint and capture actual output."

Add-PathCheck $checks "agency.cli" "Runtime" "Agency CLI entrypoint exists" `
    @("Agency/Core/cli/dashboard_cli.py", "Dashboard/Agency/Core/cli/dashboard_cli.py") `
    "Run a read-only command and capture output."

Add-PathCheck $checks "ui.project" "UI" "Godot project exists" `
    @("UI/project.godot", "Dashboard/UI/project.godot") `
    "Launch the project and record the actual scene."

Add-PathCheck $checks "workbench.main" "UI" "Workbench boot scene exists" `
    @("UI/Workbench/Main/Main.tscn", "Dashboard/UI/Workbench/Main/Main.tscn") `
    "Launch the scene and verify it remains usable."

$projectCandidates = @(
    (Join-Path $RepoRoot "UI/project.godot"),
    (Join-Path $RepoRoot "Dashboard/UI/project.godot")
)

$projectFile = $projectCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1

if ($projectFile) {
    $mainScene = Select-String -Path $projectFile -Pattern "run/main_scene" -ErrorAction SilentlyContinue | Select-Object -First 1

    if ($mainScene) {
        $checks.Add((New-Check "ui.main_scene" "UI" "Godot main scene is configured" "WIRED" "FOUND" $mainScene.Line.Trim() "Launch it; configuration is not proof it runs."))
    } else {
        $checks.Add((New-Check "ui.main_scene" "UI" "Godot main scene is configured" "NONE" "NOT FOUND" "run/main_scene was not found." "Identify the actual boot route."))
    }
}

Add-PathCheck $checks "ghost.controller" "Ghost Workflow" "Ghost command controller exists" `
    @("UI/Workbench/interaction/GhostCommandController.gd") `
    "Create one primitive from an operator action."

Add-PathCheck $checks "ghost.dialogs" "Ghost Workflow" "Ghost authoring dialogs exist" `
    @("UI/Workbench/interaction/GhostCommandDialogs.gd") `
    "Open the authoring UI and submit one command."

Add-PathCheck $checks "ghost.renderer" "Ghost Workflow" "Ghost primitive renderer exists" `
    @("UI/Workbench/rendering/GhostPrimitiveRenderer.gd") `
    "Observe a primitive rendered in the viewport."

Add-PathCheck $checks "ghost.exporter" "Ghost Workflow" "Ghost JSON exporter exists" `
    @("UI/Workbench/packet/GhostCommandExporter.gd") `
    "Export one primitive and validate the JSON."

$workbenchRoot = Join-Path $RepoRoot "UI\Workbench"
$ghostTextHits = Find-Text `
    -SearchRoot $workbenchRoot `
    -Patterns @("GhostCommandExporter", "JSON.stringify", "store_string") `
    -Extensions @("*.gd")

if ($ghostTextHits.Count -gt 0) {
    $checks.Add((New-Check "ghost.export_wiring" "Ghost Workflow" "Workbench export references are present" "WIRED" "FOUND" (($ghostTextHits | Select-Object -First 30) -join ", ") "Execute export and inspect the file."))
} else {
    $checks.Add((New-Check "ghost.export_wiring" "Ghost Workflow" "Workbench export references are present" "NONE" "NOT FOUND" "No matching references found inside UI/Workbench." "Locate or implement the export route."))
}

$jsonCandidates = Get-ChildItem -Path $RepoRoot -Recurse -File -Filter *.json -ErrorAction SilentlyContinue |
    Where-Object {
        $_.FullName -notmatch '[\\/](\.git|\.godot|archive|__pycache__|node_modules|_zip_test)[\\/]' -and
        $_.Name -match '(ghost|room|layout|candidate|assembly|packet)'
    }

if ($jsonCandidates.Count -gt 0) {
    $relativeJson = $jsonCandidates | ForEach-Object {
        $_.FullName.Substring($RepoRoot.Length).TrimStart('\', '/')
    }

    $checks.Add((New-Check "ghost.json_artifacts" "Ghost Workflow" "Candidate JSON artifacts exist" "PRESENT" "FOUND" (($relativeJson | Select-Object -First 30) -join ", ") "Determine whether any file came from the current UI workflow."))
} else {
    $checks.Add((New-Check "ghost.json_artifacts" "Ghost Workflow" "Candidate JSON artifacts exist" "NONE" "NOT FOUND" "No matching JSON artifacts found." "Export one primitive from the UI."))
}

Add-PathCheck $checks "packet.loader" "Workbench" "Packet loader exists" `
    @("UI/Workbench/packet/PacketLoader.gd") `
    "Load a known JSON packet in the running Workbench."

Add-PathCheck $checks "packet.display" "Workbench" "Packet display resolver exists" `
    @("UI/Workbench/packet/PacketDisplayResolver.gd") `
    "Select an object and verify packet details are shown."

Add-PathCheck $checks "render.packet_geometry" "Workbench" "Packet geometry renderer exists" `
    @("UI/Workbench/rendering/PacketGeometryRenderer.gd") `
    "Render geometry from a packet."

Add-PathCheck $checks "selection.raycaster" "Workbench" "Viewport selection code exists" `
    @("UI/Workbench/selection/SelectionRaycaster.gd") `
    "Click a rendered object and observe selection state."

Add-PathCheck $checks "session" "Workbench" "Workbench session state exists" `
    @("UI/Workbench/core/WorkbenchSession.gd") `
    "Load, modify, and reload without losing traceable state."

Add-PathCheck $checks "engineering.boat_assembly" "Engineering" "Active boat assembly generator exists" `
    @("Engineering/py/Projects/Float/Boat/boat_assembly.py") `
    "Run it successfully and verify generated packet fields."

Add-PathCheck $checks "engineering.hull" "Engineering" "Active hull generation scripts exist" `
    @(
        "Engineering/py/Projects/Float/Boat/Hull/hull_inventory.py",
        "Engineering/py/Projects/Float/Boat/Hull/hull_frame.py"
    ) `
    "Run each generator and capture outputs and errors."

Add-PathCheck $checks "engineering.motor" "Engineering" "Active motor and battery generators exist" `
    @(
        "Engineering/py/Projects/Float/Boat/Motor/battery.py",
        "Engineering/py/Projects/Float/Boat/Motor/motor.py"
    ) `
    "Run each generator and verify packet schema."

$archiveRoot = Join-Path $RepoRoot "Engineering\Projects\archive"

if (Test-Path $archiveRoot) {
    $archivedGenerators = Get-ChildItem `
        -Path $archiveRoot `
        -Recurse `
        -File `
        -Include boat_assembly.py, hull_inventory.py, hull_frame.py, battery.py, motor.py `
        -ErrorAction SilentlyContinue

    if ($archivedGenerators.Count -gt 0) {
        $archiveEvidence = $archivedGenerators | ForEach-Object {
            $_.FullName.Substring($RepoRoot.Length).TrimStart('\', '/')
        }

        $checks.Add((New-Check "engineering.archive_lineage" "Engineering" "Archived Float generator lineage exists" "PRESENT" "FOUND" (($archiveEvidence | Select-Object -First 30) -join ", ") "Archive presence is not active capability."))
    }
}

$smokeResults = @()

if ($RunSmokeTests) {
    $python = Get-Command python -ErrorAction SilentlyContinue
    if (-not $python) { $python = Get-Command py -ErrorAction SilentlyContinue }

    $activeScripts = @(
        "Engineering/py/Projects/Float/Boat/Hull/hull_inventory.py",
        "Engineering/py/Projects/Float/Boat/Hull/hull_frame.py",
        "Engineering/py/Projects/Float/Boat/Motor/battery.py",
        "Engineering/py/Projects/Float/Boat/Motor/motor.py",
        "Engineering/py/Projects/Float/Boat/boat_assembly.py"
    )

    if ($python) {
        foreach ($relative in $activeScripts) {
            $full = Join-Path $RepoRoot $relative

            if (Test-Path $full) {
                $output = & $python.Source $full 2>&1
                $exit = $LASTEXITCODE

                $smokeResults += [pscustomobject]@{
                    script = $relative
                    exit_code = $exit
                    output = ($output | Out-String).Trim()
                }

                $status = if ($exit -eq 0) { "PASS" } else { "FAIL" }
                $checks.Add((New-Check ("smoke." + ($relative -replace '[^A-Za-z0-9]', '_')) "Smoke Test" "Script executed" "EXECUTABLE" $status "$relative exited $exit" "Inspect generated output."))
            }
        }
    }
}

Ensure-ObservationsFile

try {
    $observationDocument = Get-Content $ObservationsPath -Raw | ConvertFrom-Json
} catch {
    throw "Unable to parse observations.json: $($_.Exception.Message)"
}

$manualDefinitions = @(
    @{ id = "demo.01"; step = "Launch the current Godot project"; pass = "Workbench opens and remains usable; fatal parser or runtime errors are not present." },
    @{ id = "demo.02"; step = "Create or load an empty room"; pass = "Room is visibly present and has a traceable source." },
    @{ id = "demo.03"; step = "Create one ghost primitive"; pass = "Primitive appears in the viewport from an operator action." },
    @{ id = "demo.04"; step = "Move, rotate, and scale the primitive"; pass = "Transforms visibly change and persist in candidate state." },
    @{ id = "demo.05"; step = "Export the ghost candidate to JSON"; pass = "A new JSON file is written with identity and transforms." },
    @{ id = "demo.06"; step = "Validate and inspect the JSON"; pass = "JSON parses and fields match the viewport candidate." },
    @{ id = "demo.07"; step = "Edit one JSON field outside Godot"; pass = "The edit is deliberate, parseable, and recorded." },
    @{ id = "demo.08"; step = "Reload the edited JSON"; pass = "Workbench reflects the edited field." },
    @{ id = "demo.09"; step = "Assign additional object detail"; pass = "Material, type, or metadata can be added without losing base geometry." },
    @{ id = "demo.10"; step = "Save and reopen the project state"; pass = "The room and object reconstruct from files, not memory." },
    @{ id = "demo.11"; step = "Trace provenance"; pass = "The producing command, file, and code path can be identified." }
)

$manual = @()

foreach ($definition in $manualDefinitions) {
    $record = Get-ObservationRecord $observationDocument $definition.id

    $manual += [pscustomobject]@{
        id = $definition.id
        step = $definition.step
        pass_condition = $definition.pass
        result = $record.result
        evidence = $record.evidence
        unresolved = $record.unresolved
    }
}

$summary = [ordered]@{
    NONE = @($checks | Where-Object { $_.evidence_level -eq "NONE" }).Count
    PRESENT = @($checks | Where-Object { $_.evidence_level -eq "PRESENT" }).Count
    WIRED = @($checks | Where-Object { $_.evidence_level -eq "WIRED" }).Count
    EXECUTABLE = @($checks | Where-Object { $_.evidence_level -eq "EXECUTABLE" }).Count
    PASS = @($manual | Where-Object { $_.result -eq "PASS" }).Count
    PARTIAL = @($manual | Where-Object { $_.result -eq "PARTIAL" }).Count
    FAIL = @($manual | Where-Object { $_.result -eq "FAIL" }).Count
    UNTESTED = @($manual | Where-Object { $_.result -eq "UNTESTED" }).Count
}

$currentTest = $manual |
    Where-Object { $_.result -ne "PASS" } |
    Select-Object -First 1

$report = [pscustomobject]@{
    schema_version = 2
    repository_root = $RepoRoot
    script_root = $ScriptRoot
    generated_at = (Get-Date).ToString("o")
    rule = "Presence is not capability. Capability requires an observed end-to-end demonstration."
    summary = [pscustomobject]$summary
    current_test = $currentTest
    checks = $checks
    smoke_tests = $smokeResults
    manual_demonstration = $manual
}

$timestamp = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"

$jsonPath = Join-Path $OutputRoot "capability_audit_$timestamp.json"
$mdPath = Join-Path $OutputRoot "capability_audit_$timestamp.md"
$latestJsonPath = Join-Path $OutputRoot "capability_state.json"
$latestMdPath = Join-Path $OutputRoot "capability_state.md"

$reportJson = $report | ConvertTo-Json -Depth 10
$reportJson | Set-Content -Path $jsonPath -Encoding UTF8
$reportJson | Set-Content -Path $latestJsonPath -Encoding UTF8

$lines = [System.Collections.Generic.List[string]]::new()
$lines.Add("# Software Capability Audit")
$lines.Add("")
$lines.Add("- Repository: ``$RepoRoot``")
$lines.Add("- Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')")
$lines.Add("- Governing rule: **Presence is not capability. Capability requires an observed end-to-end demonstration.**")
$lines.Add("")
$lines.Add("## Summary")
$lines.Add("")
$lines.Add("| State | Count |")
$lines.Add("|---|---:|")

foreach ($item in $summary.GetEnumerator()) {
    $lines.Add("| $($item.Key) | $($item.Value) |")
}

if ($currentTest) {
    $lines.Add("")
    $lines.Add("## Current capability test")
    $lines.Add("")
    $lines.Add("- ID: **$($currentTest.id)**")
    $lines.Add("- Step: $($currentTest.step)")
    $lines.Add("- Pass condition: $($currentTest.pass_condition)")
    $lines.Add("- Current result: **$($currentTest.result)**")
}

$lines.Add("")
$lines.Add("## Automated inventory")
$lines.Add("")
$lines.Add("| ID | Category | Candidate capability | Evidence level | Status | Evidence | Next proof |")
$lines.Add("|---|---|---|---|---|---|---|")

foreach ($check in $checks) {
    $evidence = ($check.evidence -replace '\|', '/' -replace "`r?`n", ' ')
    $next = ($check.next_proof -replace '\|', '/' -replace "`r?`n", ' ')

    $lines.Add("| $($check.id) | $($check.category) | $($check.capability) | $($check.evidence_level) | $($check.status) | $evidence | $next |")
}

$lines.Add("")
$lines.Add("## Manual end-to-end demonstration")
$lines.Add("")
$lines.Add("Manual results are loaded from ``UI/Workbench/audit/observations.json``.")
$lines.Add("Nothing becomes PASS from code inspection alone.")
$lines.Add("")
$lines.Add("| ID | Step | Pass condition | Result | Evidence |")
$lines.Add("|---|---|---|---|---|")

foreach ($item in $manual) {
    $evidence = ($item.evidence -replace '\|', '/' -replace "`r?`n", ' ')
    $lines.Add("| $($item.id) | $($item.step) | $($item.pass_condition) | $($item.result) | $evidence |")
}

$lines.Add("")
$lines.Add("## Capability conclusion")
$lines.Add("")
$lines.Add("> We have built candidate software surfaces toward a room -> ghost primitive -> JSON -> edit -> reload workflow. We have not yet demonstrated that workflow end to end.")
$lines.Add("")
$lines.Add("## Next development rule")
$lines.Add("")
$lines.Add("Work on the first manual capability step that is not PASS. Do not add unrelated features until that step passes or is explicitly blocked.")

$lines | Set-Content -Path $mdPath -Encoding UTF8
$lines | Set-Content -Path $latestMdPath -Encoding UTF8

Write-Host ""
Write-Host "Audit complete." -ForegroundColor Green
Write-Host "Stable JSON: $latestJsonPath"
Write-Host "Stable MD:   $latestMdPath"
Write-Host "History JSON: $jsonPath"
Write-Host "History MD:   $mdPath"
Write-Host ""

if ($currentTest) {
    Write-Host "Current capability test:" -ForegroundColor Cyan
    Write-Host "  $($currentTest.id)"
    Write-Host "  $($currentTest.step)"
    Write-Host "  Result: $($currentTest.result)"
    Write-Host ""
}

Write-Host "Summary:" -ForegroundColor Cyan

foreach ($item in $summary.GetEnumerator()) {
    Write-Host "  $($item.Key): $($item.Value)"
}