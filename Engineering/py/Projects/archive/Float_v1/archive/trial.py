from pathlib import Path
from model import FloatModel, FloatParams
from packet import build_packet


def run_trial(
    duration: float = 10.0,
    dt: float = 0.05,
    output_path: str = "float_result_packet.json",
):
    params = FloatParams()
    model = FloatModel(params)

    # Forced disturbance: start partially submerged.
    model.state.z = -0.4
    model.state.velocity = 0.0

    samples = []
    steps = int(duration / dt)

    for _ in range(steps):
        samples.append(model.step(dt))

    packet = build_packet(samples)

    out = Path(output_path)
    out.write_text(packet.to_json(), encoding="utf-8")

    print(packet.to_json())
    print(f"\nWrote packet: {out.resolve()}")


if __name__ == "__main__":
    run_trial()