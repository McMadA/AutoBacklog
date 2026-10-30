"""
Base Backlog Adapter Interface
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class BaseBacklogAdapter(ABC):
    """Abstract interface for backlog issue trackers and agile boards."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the adapter (e.g. 'Azure Boards', 'GitHub Issues')."""
        pass

    @abstractmethod
    def fetch_items(self, include_ideas: bool = False) -> List[Dict[str, Any]]:
        """
        Fetches open backlog items.
        Returns a list of dicts with standardized keys:
        {
            'id': int or str,
            'title': str,
            'type': str ('User Story', 'Bug', 'Issue', 'Task'),
            'state': str ('New', 'Active', 'Open', etc.),
            'description': str,
            'priority': int,
            'tags': List[str],
            'url': str
        }
        """
        pass

    @abstractmethod
    def get_item_details(self, item_id: Any) -> Optional[Dict[str, Any]]:
        """Fetches full details including rich description and acceptance criteria."""
        pass

    @abstractmethod
    def set_state(
        self,
        item_id: Any,
        new_state: str,
        discussion_note: Optional[str] = None,
    ) -> bool:
        """Updates the state of an item (e.g. 'Active', 'Resolved', 'Closed')."""
        pass

    @abstractmethod
    def post_discussion(self, item_id: Any, note: str) -> bool:
        """Adds a discussion comment / progress note to the item."""
        pass
