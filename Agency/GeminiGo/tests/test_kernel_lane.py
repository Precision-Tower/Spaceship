from Agency.GeminiGo.assignment import (
    KERNEL_IDENTITY,
    assignment_paths,
    bounded_evidence,
    select_assignment,
)
from Agency.GeminiGo.dispatch import (
    action_fingerprint,
    build_inspection_packet,
)


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    task = select_assignment()
    require(task is not None, "no GeminiGo assignment")
    require(
        task["identity"] == KERNEL_IDENTITY,
        repr(task),
    )
    require(task["lane"] == "kernel", repr(task))

    paths = assignment_paths(task)
    require("qps/checklist.qps" in paths, repr(paths))
    require("qps/kernel/_index.qps" in paths, repr(paths))
    require(
        all(not path.startswith("qps/cipher") for path in paths),
        repr(paths),
    )

    evidence = bounded_evidence(task)
    require("resource state first" in evidence, evidence)
    require("read-only" in evidence, evidence)

    packet = build_inspection_packet(task)
    require(
        packet.constraints["mutation_authorized"] is False,
        repr(packet.constraints),
    )
    require(
        "qps/cipher" in packet.scope["exclude"],
        repr(packet.scope),
    )
    step = packet.steps[0]
    require(
        step.constraints["read_only"] is True,
        repr(step.constraints),
    )
    require(
        step.constraints["mutation_authorized"] is False,
        repr(step.constraints),
    )
    require(
        step.request["repository_context"]["paths"] == paths,
        repr(step.request),
    )

    fingerprint = action_fingerprint(task)
    require(bool(fingerprint), fingerprint)

    print("GEMINIGO_KERNEL_LANE=PASS")


if __name__ == "__main__":
    main()
