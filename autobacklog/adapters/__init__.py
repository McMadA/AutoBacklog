"""
Backlog Adapters Package
"""

from autobacklog.adapters.azure_boards import AzureBoardsAdapter
from autobacklog.adapters.base import BaseBacklogAdapter
from autobacklog.adapters.github_issues import GitHubIssuesAdapter
from autobacklog.adapters.markdown_plan import MarkdownPlanAdapter
from autobacklog.config import AutoBacklogConfig


def get_backlog_adapter(config: AutoBacklogConfig) -> BaseBacklogAdapter:
    b_type = (config.backlog.type or "azure_boards").lower()
    if b_type in ("azure", "azure_boards", "devops"):
        return AzureBoardsAdapter(config)
    elif b_type in ("github", "github_issues", "gh"):
        return GitHubIssuesAdapter(config)
    elif b_type in ("markdown", "markdown_plan", "local"):
        return MarkdownPlanAdapter(config)
    else:
        raise ValueError(
            f"Onbekend backlog type: '{b_type}'. Kies uit 'azure_boards', 'github_issues', of 'markdown'."
        )


__all__ = [
    "BaseBacklogAdapter",
    "AzureBoardsAdapter",
    "GitHubIssuesAdapter",
    "MarkdownPlanAdapter",
    "get_backlog_adapter",
]
