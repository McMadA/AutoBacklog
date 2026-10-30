"""
Base AI Provider Interface
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Tuple


class BaseAIProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def display_name(self) -> str:
        pass

    @abstractmethod
    def find_executable(self) -> Optional[str]:
        """Locates the CLI binary on the host system."""
        pass

    @abstractmethod
    def get_default_models(self) -> Tuple[str, Optional[str], str, Optional[str]]:
        """Returns (large_primary, large_fallback, small_primary, small_fallback)."""
        pass

    @abstractmethod
    def build_cmd(self, prompt: str, model: str, effort: str = "high") -> List[str]:
        """Constructs the command invocation arguments for the CLI."""
        pass

    @abstractmethod
    def parse_quota_error(self, output: str) -> Optional[int]:
        """
        Parses error output for quota / 429 exhaustion messages.
        Returns the reset countdown in seconds, or None if no quota error found.
        """
        pass
