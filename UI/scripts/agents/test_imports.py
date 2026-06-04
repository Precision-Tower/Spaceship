# test_import.py
try:
    from UI.scripts.agents.core import WeeboAgent, CaliBridge, WeeboMemory, PathResolver
    from UI.scripts.reasoners import ReasonerFactory
    from UI.scripts.listeners import WeeboController
    print("SUCCESS: All components are correctly package-routed.")
except ImportError as e:
    print(f"FAILED: Import error detected: {e}")