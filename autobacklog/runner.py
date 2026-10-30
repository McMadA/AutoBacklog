"""
AutoBacklog Core Execution Loop
Coordinates Adapters, AI Providers, Safeguards, and Reporters.
"""

import datetime
import os
import re
import subprocess
import time
from typing import Any, Dict, List, Optional, Set, Tuple

from autobacklog.adapters import get_backlog_adapter
from autobacklog.config import AutoBacklogConfig
from autobacklog.providers import get_ai_provider
from autobacklog.reporters.dashboard import RunProgressReporter
from autobacklog.reporters.streamer import SmartConsoleStreamer
from autobacklog.safeguards.dirty_guard import (
    get_dirty_git_files,
    revert_zero_diff_item,
)
from autobacklog.safeguards.hardware import detect_connected_devices
from autobacklog.safeguards.quota_cache import (
    is_model_exhausted,
    load_quota_cache,
    record_quota_exhaustion,
)
from autobacklog.safeguards.snapshot import create_preflight_snapshot


class BacklogRunner:
    def __init__(self, config: AutoBacklogConfig):
        self.config = config
        self.ws_dir = config.workspace_dir
        self.adapter = get_backlog_adapter(config)
        self.provider = get_ai_provider(config.provider.type)
        self.reporter = RunProgressReporter(
            self.ws_dir, config.reporters.dashboard_file
        )

        quota_rel = config.safeguards.quota_cache_file
        self.quota_cache_path = os.path.join(self.ws_dir, quota_rel)

        # Models
        (
            def_l,
            def_l_fb,
            def_s,
            def_s_fb,
        ) = self.provider.get_default_models()
        self.large_model = config.provider.large_model or def_l
        self.large_fallback = config.provider.large_fallback or def_l_fb
        self.small_model = config.provider.small_model or def_s
        self.small_fallback = config.provider.small_fallback or def_s_fb

    def run(self, specific_id: Optional[int] = None):
        print("=" * 80)
        print(f"🚀 AutoBacklog - Autonome Backlog Runner")
        print(f"• Project:           {self.config.project_name}")
        print(f"• Workspace:         {self.ws_dir}")
        print(f"• Backlog Bron:      {self.adapter.name}")
        print(f"• AI Provider:       {self.provider.display_name}")
        print(f"• Grote Taken:       {self.large_model} (Fallback: {self.large_fallback or 'Geen'})")
        print(f"• Kleine Taken:      {self.small_model} (Fallback: {self.small_fallback or 'Geen'})")
        print("=" * 80)

        # 1. Pre-flight snapshot
        if self.config.safeguards.create_snapshots:
            snap_dir, zip_p, tag = create_preflight_snapshot(
                self.ws_dir,
                self.config.safeguards.snapshots_dir,
                self.config.safeguards.git_tag_prefix,
            )
            if zip_p:
                print(f"🛡️ [VEILIGHEIDSNET] Pre-flight snapshot gereed: {zip_p}")
            if tag:
                print(f"🏷️ [GIT TAG] Checkpoint aangemaakt: {tag}")
            print("-" * 80)

        round_num = 0
        exhausted_models: Set[str] = set()

        while round_num < self.config.max_rounds:
            round_num += 1

            # Fetch open items
            items = self.adapter.fetch_items(
                include_ideas=self.config.backlog.include_ideas
            )
            committed_ids = self._get_committed_ids_from_git()

            if specific_id is not None:
                items = [it for it in items if int(it["id"]) == specific_id]

            uncommitted = [
                it
                for it in items
                if int(it["id"]) not in committed_ids
                and int(it["id"]) not in self.config.backlog.non_executable_ids
            ]

            # Sort items by execution order
            ordered_items = self._sort_items(uncommitted)

            # Filter candidates based on available quota
            candidate, model, effort, tier = self._pick_next_task(
                ordered_items, exhausted_models
            )

            if not candidate:
                if not ordered_items:
                    print("\n🎉 [BACKLOG COMPLETED] Alle taken zijn voltooid en gecommit!")
                else:
                    print(
                        f"\n⏸️ [QUOTA PAUZE] Alle beschikbare modellen voor de resterende taken ({len(ordered_items)}) zijn uitgeput."
                    )
                break

            print("\n" + "=" * 80)
            print(
                f"🔄 [Ronde {round_num}/{self.config.max_rounds}] Taak #{candidate['id']} ({candidate.get('type')}): {candidate.get('title')}"
            )
            print(f"⚙️ Model: {model} ({tier}, effort={effort})")

            # Check connected hardware
            hw_devices = (
                detect_connected_devices(self.ws_dir)
                if self.config.hardware.detect_adb
                else []
            )
            if hw_devices:
                d_str = ", ".join(
                    [f"{d['brand']} {d['model']} (API {d['api_level']})" for d in hw_devices]
                )
                print(f"📱 Testapparaat online: {d_str}")
            print("=" * 80)

            # Mark item Active
            self.adapter.set_state(candidate["id"], "Active")
            self.reporter.set_current_task(candidate, model, tier)

            # Build Prompt
            prompt = self._build_prompt(candidate, hw_devices)

            start_t = time.time()
            returncode, stdout_content = self._execute_ai_task(prompt, model, effort)
            duration = time.time() - start_t

            # Inspect Output for Quota Exhaustion
            quota_sec = self.provider.parse_quota_error(stdout_content)
            if quota_sec:
                exhausted_models.add(model)
                record_quota_exhaustion(self.quota_cache_path, model, quota_sec)
                print(f"\n🚨 [MODEL QUOTA UITGEPUT] {model} gepauzeerd voor {quota_sec // 3600}h.")

            dirty_files = get_dirty_git_files(self.ws_dir)

            if returncode != 0:
                print(f"❌ [FOUT] Ronde {round_num} gestopt met code {returncode} na {duration:.1f}s.")
                if not dirty_files and self.config.safeguards.auto_revert_zero_diff:
                    revert_zero_diff_item(
                        self.adapter,
                        candidate["id"],
                        previous_state="New",
                        reason=f"CLI gestopt met foutcode {returncode} zonder codewijzigingen",
                    )
                    print(f"↩️ Taak #{candidate['id']} veilig hersteld naar 'New' op het bord.")
                self.reporter.record_failed(
                    candidate, f"Foutcode {returncode}", model
                )
            else:
                commit_hash = self._get_latest_commit_hash()
                print(f"✅ [SUCCES] Taak #{candidate['id']} voltooid in {duration:.1f}s!")
                self.adapter.set_state(
                    candidate["id"],
                    "Resolved",
                    discussion_note=f"AutoBacklog voltooid via {model} (commit: {commit_hash})",
                )
                self.reporter.record_completed(
                    candidate, duration, model, commit_hash
                )

            # Cooldown
            if self.config.cooldown_seconds > 0:
                print(f"⏳ Cooldown van {self.config.cooldown_seconds}s...")
                time.sleep(self.config.cooldown_seconds)

        print("\n🏁 AutoBacklog sessie beëindigd.")

    def _sort_items(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        pref_order = {
            t_id: idx
            for idx, t_id in enumerate(self.config.backlog.execution_order)
        }

        def sort_key(it):
            t_id = int(it["id"])
            if t_id in pref_order:
                return (0, pref_order[t_id], it.get("priority", 2))
            return (1, it.get("priority", 2), t_id)

        return sorted(items, key=sort_key)

    def _classify_task(self, item: Dict[str, Any]) -> Tuple[str, str]:
        title = item.get("title", "").lower()
        desc = item.get("description", "").lower()
        tags = [str(t).lower() for t in item.get("tags", [])]
        combined = f"{title} {desc} {' '.join(tags)}"

        if "opus" in combined:
            return "LARGE", "Explicit Opus tag"
        if "sonnet" in combined:
            return "SMALL", "Explicit Sonnet tag"

        large_kws = [
            "architectuur",
            "refactor",
            "migration",
            "schema",
            "cortex",
            "engine",
            "security",
            "pipeline",
        ]
        for kw in large_kws:
            if kw in combined:
                return "LARGE", f"Sleutelwoord '{kw}'"

        return "SMALL", "Standaard UI/Feature omvang"

    def _pick_next_task(
        self, items: List[Dict[str, Any]], exhausted: Set[str]
    ) -> Tuple[Optional[Dict[str, Any]], str, str, str]:
        for it in items:
            tier, _ = self._classify_task(it)
            if tier == "LARGE":
                m = self._resolve_model(
                    self.large_model, self.large_fallback, exhausted
                )
                effort = self.config.provider.large_effort
            else:
                m = self._resolve_model(
                    self.small_model, self.small_fallback, exhausted
                )
                effort = self.config.provider.small_effort

            if m is not None:
                return it, m, effort, tier

        return None, "", "", ""

    def _resolve_model(
        self, primary: str, fallback: Optional[str], exhausted: Set[str]
    ) -> Optional[str]:
        # Check quota cache on disk
        p_exhausted, _ = is_model_exhausted(self.quota_cache_path, primary)
        if primary not in exhausted and not p_exhausted:
            return primary
        if fallback:
            fb_exhausted, _ = is_model_exhausted(self.quota_cache_path, fallback)
            if fallback not in exhausted and not fb_exhausted:
                return fallback
        return None

    def _build_prompt(
        self, item: Dict[str, Any], hw_devices: List[dict]
    ) -> str:
        hw_section = ""
        if hw_devices:
            dev_lines = "\n".join(
                [
                    f"- {d['brand']} {d['model']} (Serial: {d['serial']}, Android API: {d['api_level']})"
                    for d in hw_devices
                ]
            )
            hw_section = f"""
================================================================================
AANGESLOTEN TESTAPPARATUUR
================================================================================
{dev_lines}
"""

        return f"""{self.config.system_prompt_intro}
Workspace: {self.ws_dir}

================================================================================
ACTIEVE TAAK
================================================================================
  ID:     #{item.get('id')} ({item.get('type')})
  Titel:  {item.get('title')}
  Status: {item.get('state')}
  Tags:   {', '.join(item.get('tags', []))}
  URL:    {item.get('url')}

BESCHRIJVING & ACCEPTATIECRITERIA:
{item.get('description')}
{hw_section}
================================================================================
ACCEPTATIE-EISEN & KWALITEITSPOORTEN
================================================================================
1. Analyseer de codebase en implementeer de oplossing conform de architectuur.
2. Schrijf gerichte unit- en integratietesten voor alle nieuwe functionaliteit.
3. Voer linting en typechecking uit en zorg dat deze 100% foutloos zijn.
4. Commit de wijzigingen met een duidelijke conventionele commit message die refereert aan #{item.get('id')}.
5. Werk documentatie en eventuele learnings/DNA bij.
6. Sluit je eindrapport ALTIJD af met exact deze marker:
   [TASK_RESULT: #{item.get('id')} COMPLETED]
"""

    def _execute_ai_task(
        self, prompt: str, model: str, effort: str
    ) -> Tuple[int, str]:
        cmd = self.provider.build_cmd(prompt, model, effort)
        streamer = SmartConsoleStreamer()
        full_output = []

        try:
            proc = subprocess.Popen(
                cmd,
                cwd=self.ws_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
            )

            for line in proc.stdout:
                full_output.append(line)
                streamer.process_line(line)

            proc.wait()
            return proc.returncode, "".join(full_output)
        except Exception as e:
            return 1, str(e)

    def _get_committed_ids_from_git(self) -> Set[int]:
        try:
            res = subprocess.run(
                ["git", "log", "-n", "300", "--pretty=format:%s %b"],
                cwd=self.ws_dir,
                capture_output=True,
                text=True,
            )
            if res.returncode == 0:
                found = re.findall(r"#(\d+)", res.stdout)
                return {int(x) for x in found}
        except Exception:
            pass
        return set()

    def _get_latest_commit_hash(self) -> str:
        try:
            res = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                cwd=self.ws_dir,
                capture_output=True,
                text=True,
            )
            if res.returncode == 0:
                return res.stdout.strip()
        except Exception:
            pass
        return "onbekend"
