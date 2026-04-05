"""
Diff Engine — compares today's scrape with yesterday's
Detects meaningful changes and scores their importance
"""

import json
import glob
import os
from datetime import datetime, timezone
from difflib import SequenceMatcher


def load_latest_two_scrapes() -> tuple:
    """Load the two most recent scrape files (relative to this script's directory)"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    pattern = os.path.join(script_dir, "scrape_*.json")
    files = sorted(glob.glob(pattern), reverse=True)

    if len(files) < 2:
        print("Not enough scrape files to diff. Need at least 2 runs.")
        return None, None

    with open(files[0]) as f:
        latest = json.load(f)
    with open(files[1]) as f:
        previous = json.load(f)

    return latest, previous


def similarity_score(text1: str, text2: str) -> float:
    """Returns similarity between 0.0 (completely different) and 1.0 (identical)"""
    return SequenceMatcher(None, text1, text2).ratio()


def diff_competitor(new_data: dict, old_data: dict) -> dict:
    """Compare two snapshots for a single competitor"""
    changes = []
    change_score = 0  # higher = more significant change

    # Check price changes
    new_prices = set(new_data.get("prices", []))
    old_prices = set(old_data.get("prices", []))

    added_prices = new_prices - old_prices
    removed_prices = old_prices - new_prices

    if added_prices:
        changes.append({
            "type": "price_added",
            "detail": f"New prices appeared: {', '.join(added_prices)}",
            "severity": "high"
        })
        change_score += 30

    if removed_prices:
        changes.append({
            "type": "price_removed",
            "detail": f"Prices disappeared: {', '.join(removed_prices)}",
            "severity": "high"
        })
        change_score += 30

    # Check plan/feature changes
    new_features = set(new_data.get("features", []))
    old_features = set(old_data.get("features", []))

    added_features = new_features - old_features
    removed_features = old_features - new_features

    if added_features:
        changes.append({
            "type": "plan_added",
            "detail": f"New plans detected: {', '.join(added_features)}",
            "severity": "medium"
        })
        change_score += 20

    if removed_features:
        changes.append({
            "type": "plan_removed",
            "detail": f"Plans removed: {', '.join(removed_features)}",
            "severity": "medium"
        })
        change_score += 20

    # Check overall content similarity
    new_text = new_data.get("raw_text", "")
    old_text = old_data.get("raw_text", "")

    if new_text and old_text:
        sim = similarity_score(new_text, old_text)
        if sim < 0.85:
            changes.append({
                "type": "content_changed",
                "detail": f"Significant page content change (similarity: {sim:.0%})",
                "severity": "medium" if sim > 0.6 else "high"
            })
            change_score += int((1 - sim) * 50)

    return {
        "competitor": new_data["name"],
        "url": new_data["url"],
        "checked_at": new_data["scraped_at"],
        "change_score": min(change_score, 100),
        "has_changes": len(changes) > 0,
        "changes": changes,
        "current_prices": new_data.get("prices", []),
        "current_plans": new_data.get("features", [])
    }


def run_diff_engine() -> list:
    """Main diff runner"""
    print("\n🔍 Running Diff Engine...")
    latest, previous = load_latest_two_scrapes()

    if not latest or not previous:
        return []

    # Index by competitor name
    latest_map = {r["name"]: r for r in latest}
    previous_map = {r["name"]: r for r in previous}

    diffs = []
    for name, new_data in latest_map.items():
        if name in previous_map:
            diff = diff_competitor(new_data, previous_map[name])
            diffs.append(diff)
            status = "⚠️  CHANGED" if diff["has_changes"] else "✓  No change"
            print(f"  {status}: {name} (score: {diff['change_score']})")
        else:
            print(f"  🆕 New competitor: {name}")

    # Save diff results relative to this script's directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(script_dir, "latest_diff.json")
    with open(output_path, "w") as f:
        json.dump(diffs, f, indent=2)

    print(f"\n✅ Diff saved to latest_diff.json")
    return diffs


if __name__ == "__main__":
    diffs = run_diff_engine()
    changes_found = [d for d in diffs if d["has_changes"]]
    print(f"\n📊 {len(changes_found)}/{len(diffs)} competitors had changes")
