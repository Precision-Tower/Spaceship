"""Compatibility entrypoint; canonical implementation is qps.cipher.cipher."""

from qps.cipher.cipher import *  # noqa: F401,F403
from qps.cipher.cipher import main

if __name__ == "__main__":
    raise SystemExit(main())
