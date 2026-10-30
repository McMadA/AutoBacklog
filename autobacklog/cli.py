"""
AutoBacklog CLI Entrypoint
"""

import argparse
import os
import sys

# Ensure UTF-8 output on Windows terminals to prevent cp1252 charmap errors
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from autobacklog import __version__
from autobacklog.adapters import get_backlog_adapter
from autobacklog.config import generate_template_config, load_config
from autobacklog.providers import get_ai_provider
from autobacklog.reporters.dashboard import RunProgressReporter
from autobacklog.runner import BacklogRunner
from autobacklog.safeguards.quota_cache import (
    clear_quota_cache,
    load_quota_cache,
)
from autobacklog.safeguards.snapshot import restore_snapshot


def main():
    parser = argparse.ArgumentParser(
        prog="autobacklog",
        description="AutoBacklog - Autonomous, Resilient AI Backlog Runner",
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    subparsers = parser.add_subparsers(dest="command", help="Subcommando's")

    # 1. RUN
    run_parser = subparsers.add_parser("run", help="Start de autonome backlog loop")
    run_parser.add_argument(
        "--id", type=int, default=None, help="Specifiek taak ID uitvoeren"
    )
    run_parser.add_argument(
        "--config", type=str, default=None, help="Pad naar autobacklog.yaml"
    )
    run_parser.add_argument(
        "--provider",
        choices=["auto", "agy", "claude"],
        default=None,
        help="AI Provider override",
    )
    run_parser.add_argument(
        "--large-model", type=str, default=None, help="Model voor grote taken"
    )
    run_parser.add_argument(
        "--small-model", type=str, default=None, help="Model voor kleine taken"
    )
    run_parser.add_argument(
        "--rounds", type=int, default=None, help="Maximaal aantal rondes"
    )

    # 2. INIT
    init_parser = subparsers.add_parser(
        "init", help="Genereer een nieuw autobacklog.yaml configuratiebestand"
    )
    init_parser.add_argument(
        "--type",
        choices=["azure", "github", "markdown"],
        default="azure",
        help="Type backlog adapter template",
    )
    init_parser.add_argument(
        "--force",
        action="store_true",
        help="Overschrijf bestaand configuratiebestand",
    )

    # 3. DRY-RUN
    dry_parser = subparsers.add_parser(
        "dry-run", help="Bekijk open taken en modeltoewijzing zonder AI uit te voeren"
    )
    dry_parser.add_argument(
        "--config", type=str, default=None, help="Pad naar autobacklog.yaml"
    )
    dry_parser.add_argument(
        "--include-ideas", action="store_true", help="Neem ideeën mee"
    )

    # 4. SUMMARY
    summary_parser = subparsers.add_parser(
        "summary", help="Toon het huidige RUN_SUMMARY.md dashboard"
    )
    summary_parser.add_argument(
        "--config", type=str, default=None, help="Pad naar autobacklog.yaml"
    )

    # 5. RESTORE
    restore_parser = subparsers.add_parser(
        "restore", help="Herstel het meest recente ZIP snapshot"
    )

    # 6. CLEAR QUOTA CACHE
    clear_parser = subparsers.add_parser(
        "clear-quota", help="Wis de actieve rate-limit / model quota cache"
    )

    # 7. UI / WEB INTERFACE
    ui_parser = subparsers.add_parser(
        "ui", aliases=["web"], help="Start de lokale webinterface in de browser (voor CLI noobs)"
    )
    ui_parser.add_argument(
        "--port", type=int, default=8080, help="Poort voor de webserver (standaard: 8080)"
    )
    ui_parser.add_argument(
        "--no-browser", action="store_true", help="Open browser niet automatisch"
    )
    ui_parser.add_argument(
        "--config", type=str, default=None, help="Pad naar autobacklog.yaml"
    )

    args = parser.parse_args()

    # Default to 'run' if no subcommand provided
    if not args.command:
        # Default behavior: run
        cfg = load_config()
        runner = BacklogRunner(cfg)
        runner.run()
        return

    if args.command in ("ui", "web"):
        from autobacklog.ui import start_web_ui
        cfg = load_config(args.config)
        start_web_ui(config=cfg, port=args.port, open_browser=not args.no_browser)
        sys.exit(0)

    if args.command == "init":
        target = os.path.join(os.getcwd(), "autobacklog.yaml")
        if os.path.exists(target) and not args.force:
            print(f"❌ {target} bestaat al. Gebruik --force om te overschrijven.")
            sys.exit(1)
        template = generate_template_config(args.type)
        with open(target, "w", encoding="utf-8", newline="\n") as f:
            f.write(template)
        print(f"✅ Configuratiebestand aangemaakt op: {target}")
        print("💡 Pas het bestand aan met je eigen Azure/GitHub/Markdown gegevens en voer uit: autobacklog run")
        sys.exit(0)

    if args.command == "restore":
        cfg = load_config()
        ok = restore_snapshot(cfg.workspace_dir, cfg.safeguards.snapshots_dir)
        sys.exit(0 if ok else 1)

    if args.command == "clear-quota":
        cfg = load_config()
        q_path = os.path.join(cfg.workspace_dir, cfg.safeguards.quota_cache_file)
        clear_quota_cache(q_path)
        print(f"🧹 Quota cache gewist op: {q_path}")
        sys.exit(0)

    if args.command == "summary":
        cfg = load_config(args.config)
        s_path = os.path.join(cfg.workspace_dir, cfg.reporters.dashboard_file)
        if os.path.exists(s_path):
            with open(s_path, "r", encoding="utf-8") as f:
                print(f.read())
        else:
            print(f"ℹ️ Nog geen samenvatting gevonden op {s_path}")
        sys.exit(0)

    if args.command == "dry-run":
        cfg = load_config(args.config)
        if args.include_ideas:
            cfg.backlog.include_ideas = True
        runner = BacklogRunner(cfg)

        items = runner.adapter.fetch_items(include_ideas=cfg.backlog.include_ideas)
        committed = runner._get_committed_ids_from_git()
        uncommitted = [
            it
            for it in items
            if int(it["id"]) not in committed
            and int(it["id"]) not in cfg.backlog.non_executable_ids
        ]
        ordered = runner._sort_items(uncommitted)
        q_cache = load_quota_cache(runner.quota_cache_path)

        print("\n" + "=" * 80)
        print("🔍 [DRY RUN - BACKLOG & MODEL SELECTIE]")
        print("=" * 80)
        print(f"• Backlog Bron:   {runner.adapter.name}")
        print(f"• AI Provider:    {runner.provider.display_name}")
        print(f"• Grote Taken:    {runner.large_model}")
        print(f"• Kleine Taken:   {runner.small_model}")
        if q_cache:
            print(
                "• Quota Status:   "
                + ", ".join([f"{m}: ⏸️ Quota ({info.get('remaining_str')})" for m, info in q_cache.items()])
            )
        print(f"• Reeds gecommit: {len(committed)} taken")
        print(f"• Openstaand:     {len(ordered)} taken\n")

        for idx, it in enumerate(ordered[:15], 1):
            tier, reason = runner._classify_task(it)
            model = runner.large_model if tier == "LARGE" else runner.small_model
            badge = f"🔥 GROOT -> {model}" if tier == "LARGE" else f"⚡ KLEIN -> {model}"
            print(f"{idx:2d}. [#{it['id']}] ({it.get('type')}) {it.get('title')}")
            print(f"    └─ {badge} | {reason}")

        print("=" * 80 + "\n")
        sys.exit(0)

    if args.command == "run":
        cfg = load_config(args.config)
        if args.provider:
            cfg.provider.type = args.provider
        if args.large_model:
            cfg.provider.large_model = args.large_model
        if args.small_model:
            cfg.provider.small_model = args.small_model
        if args.rounds:
            cfg.max_rounds = args.rounds

        runner = BacklogRunner(cfg)
        runner.run(specific_id=args.id)


if __name__ == "__main__":
    main()
