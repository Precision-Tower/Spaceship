"""Compatibility entrypoint; canonical implementation is qps.cipher.source_adapter."""

from qps.cipher.source_adapter import *  # noqa: F401,F403
from qps.cipher.source_adapter import main

if __name__ == "__main__":
    raise SystemExit(main())
