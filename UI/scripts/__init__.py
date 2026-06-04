#/home/spaztic/Core/Dashboard/UI/scripts/__init__.py

"""
Core System Package
This package acts as the unified interface for WEEBO agents and the CLI spine.
"""

# Expose key modules so they can be accessed via:
# from UI.scriptsipts import agents, cli
from . import agents
from .import cli

# Optional: Add versioning or metadata
__version__ = "2.0.0"

# This ensures that when you run 'from UI.scriptsipts import ...', 
# these components are immediately available.
__all__ = ["agents", "cli"]