from __future__ import annotations

from pathlib import Path

from Engineering.py.cipher.ir.nodes import DependencyRef
from .native_binary import NativeBinaryCapability


def render_native_library_leaf(
    dependency: DependencyRef,
    capability: NativeBinaryCapability,
) -> str:
    if capability.state != "resolved":
        raise ValueError(
            "Native library leaf requires a resolved capability."
        )

    if capability.binary is None:
        raise ValueError(
            "Resolved native capability has no binary path."
        )

    module = (
        dependency.module
        or dependency.package
        or ""
    )

    symbol = dependency.symbol

    if not symbol:
        raise ValueError(
            "Native library leaf requires a source symbol."
        )

    binary = capability.binary.resolve()

    return f'''{symbol}.

identity- "{capability.identity}";

source: (
family- "Python";
module- "{module}";
symbol- "{symbol}";
);

implementation: (
family- "native-binary";
library- "{binary.name}";
native_lookup- "{symbol}";
resolver- "host-native-binary";
);

proof: (
state- "resolved";
observed_architecture- "{capability.architecture or "unknown"}";
exported_matches- {len(capability.symbols)};
);

rules: (
canonical_identity- "Source aliases do not alter this library identity";
host_path_boundary- "Physical binary paths are resolved by the current host and are not canonical library identity";
reuse- "Later Cipher conversions reuse this indexed symbol rather than duplicate it";
);
'''
