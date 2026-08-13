#!/usr/bin/python
"""
One-time remediation for the inflated "Available" count.

Background: on 2026-06-18 (commit 236789c0) a single auto-update run flipped
~587 apps N->Y. The old detector marked any page containing "TestFlight" as
Available, and Apple served its generic anti-bot interstitial page for most of
those requests. Those false-Y entries still carry last_modify="2026-06-18".

detect_testflight_status is now fixed, but we cannot reliably re-fetch the true
status from Apple: its anti-bot serves the generic interstitial cumulatively
(per-IP rate limiting), so a bulk re-check just gets interstitials and would
guess wrong. Instead, this script restores each suspect entry to its last-known-
good status from git history — the state right before the bad flip (commit
236789c0^). Entries that have genuinely changed since are picked up by later
daily update_status.py runs now that the detector is fixed.

Only the `status` field is restored; app_name/tables are left as-is.

Requires full git history (run locally, not in a shallow checkout):
  python fix_status.py              # restore suspect entries (Y + 2026-06-18)
  python fix_status.py --dry-run    # show what would change, write nothing
"""
import argparse
import json
import subprocess
import sys

from utils import TODAY, renew_readme, load_links, save_links

# Windows console defaults to a locale codec (e.g. GBK) that can't encode some
# app names; never let a print crash the remediation.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

BAD_COMMIT = "236789c0"          # the 2026-06-18 mass false-flip
SUSPECT_DATE = "2026-06-18"
LINKS_JSON_REL = "data/links.json"  # relative to repo root (for git show)


def load_pre_flip_status():
    """Return {key: status} as of the commit just before the bad flip."""
    out = subprocess.check_output(["git", "show", f"{BAD_COMMIT}^:{LINKS_JSON_REL}"])
    data = json.loads(out.decode("utf-8"))
    return {k: v.get("status") for k, v in data.get("_links", {}).items()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="report only, write nothing")
    args = parser.parse_args()

    pre_status = load_pre_flip_status()
    links_data = load_links()
    all_links = links_data["_links"]

    from collections import Counter
    changes = Counter()
    restored = 0

    for key, info in all_links.items():
        if info.get("status") != "Y" or info.get("last_modify") != SUSPECT_DATE:
            continue
        if key not in pre_status:
            continue
        before = pre_status[key]
        if before and before != info.get("status"):
            changes[(info["status"], before)] += 1
            info["status"] = before
            info["last_modify"] = TODAY
            restored += 1
            print(f"[info] {info.get('app_name', 'Unknown')} ({key}): Y -> {before}")

    print()
    print(f"[info] Suspect entries scanned, {restored} status value(s) restored")
    for (frm, to), n in changes.items():
        print(f"[info]   {frm} -> {to}: {n}")

    if args.dry_run:
        print("[info] --dry-run: no files written.")
        return

    if restored:
        save_links(links_data)
        renew_readme()
        print(f"[info] Wrote data/links.json and regenerated README.md")
    else:
        print("[info] Nothing to restore.")


if __name__ == "__main__":
    main()
