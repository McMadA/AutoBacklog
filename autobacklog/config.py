"""
AutoBacklog Configuration Loader
Loads settings from autobacklog.yaml, environment variables, or default parameters.
"""

import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

try:
    import yaml
except ImportError:
    yaml = None


@dataclass
class BacklogConfig:
    type: str = "azure_boards"  # 'azure_boards', 'github_issues', or 'markdown'
    org_url: str = ""
    project: str = ""
    repo: str = ""
    file_path: str = ""
    wiql: Optional[str] = None
    execution_order: List[int] = field(default_factory=list)
    non_executable_ids: List[int] = field(default_factory=list)
    include_ideas: bool = False
    offline_cache_file: str = "_snapshots/backlog_offline_cache.json"


@dataclass
class ProviderConfig:
    type: str = "auto"  # 'auto', 'agy', or 'claude'
    large_model: Optional[str] = None
    large_fallback: Optional[str] = None
    small_model: Optional[str] = None
    small_fallback: Optional[str] = None
    large_effort: str = "high"
    small_effort: str = "high"


@dataclass
class SafeguardsConfig:
    create_snapshots: bool = True
    snapshots_dir: str = "_snapshots"
    git_tag_prefix: str = "checkpoint-night"
    auto_revert_zero_diff: bool = True
    quota_cache_file: str = "_snapshots/model_quota_cache.json"


@dataclass
class ReportersConfig:
    dashboard_file: str = "RUN_SUMMARY.md"
    stream_console: bool = True
    console_dedup: bool = True


@dataclass
class HardwareConfig:
    detect_adb: bool = True
    adb_path: Optional[str] = None


@dataclass
class AutoBacklogConfig:
    project_name: str = "Project"
    workspace_dir: str = os.getcwd()
    system_prompt_intro: str = "You are an autonomous Senior Software Engineer."
    max_rounds: int = 1000
    cooldown_seconds: int = 10
    backlog: BacklogConfig = field(default_factory=BacklogConfig)
    provider: ProviderConfig = field(default_factory=ProviderConfig)
    safeguards: SafeguardsConfig = field(default_factory=SafeguardsConfig)
    reporters: ReportersConfig = field(default_factory=ReportersConfig)
    hardware: HardwareConfig = field(default_factory=HardwareConfig)


def load_config(
    config_path: Optional[str] = None, workspace_dir: Optional[str] = None
) -> AutoBacklogConfig:
    ws_dir = os.path.abspath(workspace_dir or os.getcwd())
    cfg = AutoBacklogConfig(workspace_dir=ws_dir)

    search_paths = []
    if config_path:
        search_paths.append(config_path)
    else:
        search_paths.extend(
            [
                os.path.join(ws_dir, "autobacklog.yaml"),
                os.path.join(ws_dir, "autobacklog.yml"),
                os.path.join(ws_dir, ".autobacklog.yaml"),
                os.path.join(ws_dir, ".autobacklog.yml"),
            ]
        )

    found_path = None
    for p in search_paths:
        if os.path.exists(p):
            found_path = p
            break

    if found_path and yaml:
        try:
            with open(found_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}

            if "project_name" in data:
                cfg.project_name = data["project_name"]
            if "system_prompt_intro" in data:
                cfg.system_prompt_intro = data["system_prompt_intro"]
            if "max_rounds" in data:
                cfg.max_rounds = int(data["max_rounds"])
            if "cooldown_seconds" in data:
                cfg.cooldown_seconds = int(data["cooldown_seconds"])

            if "backlog" in data and isinstance(data["backlog"], dict):
                b = data["backlog"]
                cfg.backlog.type = b.get("type", cfg.backlog.type)
                cfg.backlog.org_url = b.get("org_url", cfg.backlog.org_url)
                cfg.backlog.project = b.get("project", cfg.backlog.project)
                cfg.backlog.repo = b.get("repo", cfg.backlog.repo)
                cfg.backlog.file_path = b.get("file_path", cfg.backlog.file_path)
                cfg.backlog.wiql = b.get("wiql", cfg.backlog.wiql)
                cfg.backlog.execution_order = [
                    int(x) for x in b.get("execution_order", [])
                ]
                cfg.backlog.non_executable_ids = [
                    int(x) for x in b.get("non_executable_ids", [])
                ]
                cfg.backlog.include_ideas = bool(
                    b.get("include_ideas", cfg.backlog.include_ideas)
                )

            if "provider" in data and isinstance(data["provider"], dict):
                pv = data["provider"]
                cfg.provider.type = pv.get("type", cfg.provider.type)
                cfg.provider.large_model = pv.get("large_model")
                cfg.provider.large_fallback = pv.get("large_fallback")
                cfg.provider.small_model = pv.get("small_model")
                cfg.provider.small_fallback = pv.get("small_fallback")
                cfg.provider.large_effort = pv.get(
                    "large_effort", cfg.provider.large_effort
                )
                cfg.provider.small_effort = pv.get(
                    "small_effort", cfg.provider.small_effort
                )

            if "safeguards" in data and isinstance(data["safeguards"], dict):
                sg = data["safeguards"]
                cfg.safeguards.create_snapshots = bool(
                    sg.get("create_snapshots", cfg.safeguards.create_snapshots)
                )
                cfg.safeguards.snapshots_dir = sg.get(
                    "snapshots_dir", cfg.safeguards.snapshots_dir
                )
                cfg.safeguards.auto_revert_zero_diff = bool(
                    sg.get(
                        "auto_revert_zero_diff",
                        cfg.safeguards.auto_revert_zero_diff,
                    )
                )

            if "reporters" in data and isinstance(data["reporters"], dict):
                rep = data["reporters"]
                cfg.reporters.dashboard_file = rep.get(
                    "dashboard_file", cfg.reporters.dashboard_file
                )
                cfg.reporters.stream_console = bool(
                    rep.get("stream_console", cfg.reporters.stream_console)
                )

            if "hardware" in data and isinstance(data["hardware"], dict):
                hw = data["hardware"]
                cfg.hardware.detect_adb = bool(
                    hw.get("detect_adb", cfg.hardware.detect_adb)
                )

        except Exception as e:
            print(f"⚠️ [CONFIG] Kon {found_path} niet volledig laden: {e}")

    # Environment overrides
    if "AUTOBACKLOG_PROVIDER" in os.environ:
        cfg.provider.type = os.environ["AUTOBACKLOG_PROVIDER"]
    if "AUTOBACKLOG_LARGE_MODEL" in os.environ:
        cfg.provider.large_model = os.environ["AUTOBACKLOG_LARGE_MODEL"]
    if "AUTOBACKLOG_SMALL_MODEL" in os.environ:
        cfg.provider.small_model = os.environ["AUTOBACKLOG_SMALL_MODEL"]

    return cfg


def generate_template_config(flavor: str = "azure") -> str:
    if flavor == "github":
        return """# AutoBacklog Configuration (GitHub Issues)
project_name: "MyProject"
system_prompt_intro: "You are an autonomous Senior Software Engineer for this repository."
max_rounds: 500
cooldown_seconds: 10

backlog:
  type: "github_issues"
  repo: "owner/repo" # e.g. "octocat/hello-world" (defaults to current git origin)
  execution_order: []
  non_executable_ids: []
  include_ideas: false

provider:
  type: "auto" # 'auto', 'agy' (Google Antigravity), or 'claude' (Anthropic Claude Code)
  # large_model: "gemini-4-argon-high"
  # small_model: "gemini-3.8-flash-high"

safeguards:
  create_snapshots: true
  snapshots_dir: "_snapshots"
  auto_revert_zero_diff: true

reporters:
  dashboard_file: "RUN_SUMMARY.md"
  stream_console: true
"""
    elif flavor == "markdown":
        return """# AutoBacklog Configuration (Local Markdown Plan)
project_name: "MyProject"
system_prompt_intro: "You are an autonomous Senior Software Engineer for this repository."
max_rounds: 500
cooldown_seconds: 10

backlog:
  type: "markdown"
  file_path: "docs/PLAN.md" # Path to markdown plan containing `#123 Title` or `- [ ] Title`
  execution_order: []
  non_executable_ids: []

provider:
  type: "auto"

safeguards:
  create_snapshots: true
  snapshots_dir: "_snapshots"
  auto_revert_zero_diff: true

reporters:
  dashboard_file: "RUN_SUMMARY.md"
  stream_console: true
"""
    else:  # Azure Boards
        return """# AutoBacklog Configuration (Azure DevOps Boards)
project_name: "MyProject"
system_prompt_intro: "You are an autonomous Senior Software Engineer for this repository."
max_rounds: 1000
cooldown_seconds: 10

backlog:
  type: "azure_boards"
  org_url: "https://dev.azure.com/your-org"
  project: "YourProject"
  # Optional custom WIQL query
  # wiql: "SELECT [System.Id],[System.Title] FROM WorkItems WHERE [System.TeamProject]='YourProject' AND [System.State] NOT IN ('Closed','Resolved')"
  execution_order: []
  non_executable_ids: []
  include_ideas: false

provider:
  type: "auto" # 'auto', 'agy' (Google Antigravity), or 'claude' (Anthropic Claude Code)
  # large_model: "gemini-4-argon-high"
  # small_model: "gemini-3.8-flash-high"

safeguards:
  create_snapshots: true
  snapshots_dir: "_snapshots"
  auto_revert_zero_diff: true

reporters:
  dashboard_file: "RUN_SUMMARY.md"
  stream_console: true
"""
