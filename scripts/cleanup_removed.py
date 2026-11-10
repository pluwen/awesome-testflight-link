#!/usr/bin/python
"""清理 Removed 状态超过保留期（默认 30 天）的失效链接。

每天由 update_status.py 在状态更新后自动调用；
也可手动运行：
  python3 scripts/cleanup_removed.py
  python3 scripts/cleanup_removed.py --days 30 --dry-run
"""
import argparse
import datetime

from utils import load_links, save_links, renew_readme

REMOVED_RETENTION_DAYS = 30


def cleanup_removed_links(links_data, retention_days=REMOVED_RETENTION_DAYS):
    """删除 status='D' 且进入 Removed 超过 retention_days 的链接。

    last_modify 只在状态变化时刷新，因此对 'D' 条目它就是进入 Removed 的日期。
    返回被删除的 (link_id, app_name, last_modify) 列表。
    """
    all_links = links_data.get("_links", {})
    cutoff = (
        datetime.datetime.now(datetime.timezone.utc).date()
        - datetime.timedelta(days=retention_days)
    )

    removed = []
    for link_id, info in all_links.items():
        if info.get('status') != 'D':
            continue
        last_modify = info.get('last_modify', '')
        try:
            entered_removed = datetime.date.fromisoformat(last_modify)
        except ValueError:
            print(f"[warn] {link_id} - invalid last_modify '{last_modify}', skipped")
            continue
        if entered_removed < cutoff:
            removed.append((link_id, info.get('app_name', 'Unknown'), last_modify))

    for link_id, app_name, last_modify in removed:
        del all_links[link_id]
        print(f"[info] Deleted '{app_name}' ({link_id}) - Removed since {last_modify}")

    return removed


def main():
    parser = argparse.ArgumentParser(
        description="Clean up Removed links older than the retention period"
    )
    parser.add_argument(
        '--days', type=int, default=REMOVED_RETENTION_DAYS,
        help=f"retention days (default: {REMOVED_RETENTION_DAYS})"
    )
    parser.add_argument(
        '--dry-run', action='store_true',
        help="only show what would be deleted, don't modify files"
    )
    args = parser.parse_args()

    links_data = load_links()
    removed = cleanup_removed_links(links_data, args.days)

    if not removed:
        print("[info] No expired Removed links")
        return

    if args.dry_run:
        print(f"[info] Dry run: {len(removed)} links would be deleted")
        return

    save_links(links_data)
    renew_readme()
    print(f"[info] Deleted {len(removed)} links, README regenerated")


if __name__ == "__main__":
    main()
