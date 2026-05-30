import requests
import time
from collections import defaultdict

packages = ["redis-flags", "redis-feature-flags"]

BASE = "https://pypistats.org/api/packages"


# ---------------------------------------------------------
# HTTP HELPER
# ---------------------------------------------------------
def get_json(url, retries=3):

    for attempt in range(retries):

        r = requests.get(
            url,
            headers={
                "User-Agent": "pypi-stats-script/1.0"
            }
        )

        if r.status_code == 200:
            return r.json()

        if r.status_code == 429:
            wait = 2 ** attempt
            print(f"Rate limited. Waiting {wait}s...")
            time.sleep(wait)
            continue

        if r.status_code == 404:
            return None

        print(f"ERROR {r.status_code}: {url}")
        return None

    return None


# ---------------------------------------------------------
# AGGREGATION
# ---------------------------------------------------------
def aggregate(rows):

    agg = defaultdict(int)

    for row in rows:

        key = row["category"]

        if key is None:
            key = "unknown"

        agg[key] += row["downloads"]

    return sorted(
        agg.items(),
        key=lambda x: x[1],
        reverse=True
    )


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------
for pkg in packages:

    print("\n" + "=" * 60)
    print(f"PACKAGE: {pkg}")
    print("=" * 60)

    # -----------------------------------------------------
    # OVERALL
    # -----------------------------------------------------
    overall = get_json(
        f"{BASE}/{pkg}/overall"
    )

    if not overall:
        continue

    data = overall["data"]

    with_mirrors = sum(
        d["downloads"]
        for d in data
        if d["category"] == "with_mirrors"
    )

    without_mirrors = sum(
        d["downloads"]
        for d in data
        if d["category"] == "without_mirrors"
    )

    print("\n[OVERALL]")
    print(f"With mirrors:    {with_mirrors:,}")
    print(f"Without mirrors: {without_mirrors:,}")

    if with_mirrors:
        share = without_mirrors / with_mirrors * 100
        print(f"Real-user share: {share:.2f}%")

    # -----------------------------------------------------
    # RECENT
    # -----------------------------------------------------
    recent = get_json(
        f"{BASE}/{pkg}/recent"
    )

    if recent:

        d = recent["data"]

        print("\n[RECENT]")
        print(f"Last day:   {d['last_day']:,}")
        print(f"Last week:  {d['last_week']:,}")
        print(f"Last month: {d['last_month']:,}")

    # -----------------------------------------------------
    # DAILY HISTORY
    # -----------------------------------------------------
    history = get_json(
        f"{BASE}/{pkg}/overall?mirrors=false"
    )

    if history:

        print("\n[DAILY DOWNLOADS]")

        rows = history["data"]

        for row in rows[-14:]:

            date = row["date"]
            downloads = row["downloads"]

            print(
                f"{date} : {downloads:>4}"
            )

    # -----------------------------------------------------
    # PYTHON MAJOR
    # -----------------------------------------------------
    pyvers = get_json(
        f"{BASE}/{pkg}/python_major"
    )

    if pyvers:

        print("\n[PYTHON VERSIONS]")

        aggregated = aggregate(pyvers["data"])

        for version, downloads in aggregated:

            if version == "unknown":
                continue

            print(
                f"{version:<10} {downloads:>8,}"
            )

    # -----------------------------------------------------
    # SYSTEMS
    # -----------------------------------------------------
    systems = get_json(
        f"{BASE}/{pkg}/system"
    )

    if systems:

        print("\n[SYSTEMS]")

        aggregated = aggregate(systems["data"])

        for system, downloads in aggregated:

            if system == "unknown":
                continue

            print(
                f"{system:<15} {downloads:>8,}"
            )

print("\nDONE")