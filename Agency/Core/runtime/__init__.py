"""
Runtime support package.

Active local model interface:
- model_service

Legacy model_runner remains as a file for reference but is not exported as the
active runtime path because it depends on missing isolated_inference.py.
"""


def ask_model(*args, **kwargs):
    from .model_service import ask_model as _ask_model

    return _ask_model(*args, **kwargs)


def status(*args, **kwargs):
    from .model_service import status as _status

    return _status(*args, **kwargs)


__all__ = [
    "ask_model",
    "status",
]
