"""
AutoBacklog - Autonomous, Resilient AI Backlog Runner
Copyright (c) 2026 Allard Broer & Contributors.
"""

__version__ = "0.1.0"
__author__ = "Allard Broer"

from autobacklog.config import AutoBacklogConfig, load_config
from autobacklog.runner import BacklogRunner

__all__ = ["AutoBacklogConfig", "load_config", "BacklogRunner", "__version__"]
