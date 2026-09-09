from qps.cipher.emit.qps_emitter import emit_qps
from qps.cipher.ir.document import CipherDocument
from qps.cipher.ir.nodes import CipherNode


def test_emitter_is_deterministic():
    document = CipherDocument(
        children=[
            CipherNode(
                kind="term",
                name="pipe",
                children=[
                    CipherNode(
                        kind="item",
                        name="length",
                        value=100,
                    )
                ],
            )
        ]
    )

    assert emit_qps(document) == emit_qps(document)
