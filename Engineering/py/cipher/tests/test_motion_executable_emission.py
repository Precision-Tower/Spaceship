from pathlib import Path

from Engineering.py.cipher.emit.qps_emitter import emit_qps
from Engineering.py.cipher.graph.merge import merge_local_python


def main():
    root = Path(__file__).resolve().parents[4]

    merged = merge_local_python(
        root / "Engineering/py/Physics/Domains/motion.py",
        root,
    )

    qps = emit_qps(merged.document)

    assert "GRAVITY_EARTH_M_S2- 9.80665;" in qps
    assert "-func weight_force_n(" in qps
    assert "mass_kg-/n;" in qps
    assert (
        "gravity_m_s2- GRAVITY_EARTH_M_S2/n;"
        in qps
    )
    assert "%value: mass_kg * gravity_m_s2" in qps
    assert "-return value;" in qps

    print(qps)
    print("Cipher motion executable emission: PASS")


if __name__ == "__main__":
    main()
