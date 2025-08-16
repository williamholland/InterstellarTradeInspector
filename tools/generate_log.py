"""
Generate a realistic log.csv of port calls for each vessel.

Reads:
  - data/planet.csv   (id,name,mass,status)
  - data/vessel.csv   (id,name,captain,type,flag)

Writes:
  - data/log.csv      (id,port,arrival,departure,vessel)

Behaviour & design decisions:
  - Each vessel gets at least one log entry whose arrival is sometime in June 2973.
  - Each vessel may have a number of previous stops (0..n) generated backwards in time.
  - Arrival/departure are integer UNIX timestamps (UTC seconds).
  - Durations (stay and travel) are sampled from type-dependent ranges to give believable
    port-call patterns (e.g. passenger liners: many passengers, longer stays; couriers: short stays).
  - Ports (planet ids) are sampled from planet.csv with light weighting by planet status;
    final June 2973 port is biased toward the vessel's flag planet sometimes.
  - The CSV contains an auto-incrementing `id` per log row.
Usage:
    python tools/generate_logs.py --seed 42 --out data/log.csv
"""

from pathlib import Path
import csv
import random
import argparse
from datetime import datetime, timezone, timedelta

PLANET_CSV = Path("data/planet.csv")
VESSEL_CSV = Path("data/vessel.csv")
OUT_CSV = Path("data/log.csv")

# Weights to prefer selecting planets for port calls by status
PLANET_STATUS_WEIGHTS = {
    "normal": 1.0,
    "frontier": 0.6,
    "restricted": 0.4,
    "quarantine": 0.2,
    "embargo": 0.15,
}

# Type-normalisation helpers: map free-form vessel type to canonical key
TYPE_MAP = {
    "passenger liner": ["passenger liner", "liner", "passenger"],
    "interstellar shuttle": ["shuttle"],
    "private yacht": ["yacht", "private"],
    "bulk freighter": ["bulk freighter", "bulk", "freighter"],
    "container hauler": ["container", "hauler"],
    "tanker": ["tanker"],
    "fast courier": ["courier", "fast courier"],
    "research vessel": ["research"],
    "mining barge": ["mining"],
    "patrol corvette": ["patrol", "corvette"],
    "medical relief ship": ["medical"],
    "customs cutter": ["customs", "cutter"],
}

# Profiles per canonical type:
# each entry: {
#   "prev_range": (min_prev, max_prev),  # how many previous stops to generate
#   "stay_hours": (min_hours, max_hours),  # typical port stay
#   "travel_hours": (min_hours, max_hours)  # typical travel time between ports
# }
TYPE_PROFILES = {
    "passenger liner":      {"prev_range": (2, 6),  "stay_hours": (12, 72),   "travel_hours": (24, 240)},
    "interstellar shuttle": {"prev_range": (1, 4),  "stay_hours": (2, 10),    "travel_hours": (6, 48)},
    "private yacht":        {"prev_range": (0, 3),  "stay_hours": (4, 48),    "travel_hours": (12, 120)},
    "bulk freighter":       {"prev_range": (1, 5),  "stay_hours": (12, 96),   "travel_hours": (48, 480)},
    "container hauler":     {"prev_range": (1, 5),  "stay_hours": (12, 96),   "travel_hours": (48, 360)},
    "tanker":               {"prev_range": (1, 4),  "stay_hours": (24, 120),  "travel_hours": (48, 360)},
    "fast courier":         {"prev_range": (1, 4),  "stay_hours": (1, 12),    "travel_hours": (6, 72)},
    "research vessel":      {"prev_range": (1, 6),  "stay_hours": (24, 168),  "travel_hours": (24, 480)},
    "mining barge":         {"prev_range": (1, 6),  "stay_hours": (24, 240),  "travel_hours": (48, 720)},
    "patrol corvette":      {"prev_range": (0, 3),  "stay_hours": (6, 72),    "travel_hours": (12, 120)},
    "medical relief ship":  {"prev_range": (1, 4),  "stay_hours": (24, 168),  "travel_hours": (24, 240)},
    "customs cutter":       {"prev_range": (0, 4),  "stay_hours": (6, 24),    "travel_hours": (12, 120)},
}

# Fallback profile if type unknown
DEFAULT_PROFILE = {"prev_range": (0, 3), "stay_hours": (6, 48), "travel_hours": (12, 120)}

# Final-arrival bias: probability that the June 2973 arrival will be at the vessel's flag planet
FINAL_PORT_FLAG_BIAS = 0.35

# June 2973 window (we will pick a random timestamp within this month)
JUNE_YEAR = 2973
JUNE_MONTH = 6
JUNE_DAY_MIN = 1
JUNE_DAY_MAX = 28  # keep safe for generating previous stops

def parse_args():
    p = argparse.ArgumentParser(description="Generate log.csv from planet and vessel CSVs.")
    p.add_argument("--planets", type=Path, default=PLANET_CSV, help="Path to planet.csv")
    p.add_argument("--vessels", type=Path, default=VESSEL_CSV, help="Path to vessel.csv")
    p.add_argument("--out", type=Path, default=OUT_CSV, help="Output path for log.csv")
    p.add_argument("--seed", type=int, default=None, help="Random seed")
    p.add_argument("--max-prev", type=int, default=8, help="Hard cap on previous stops per vessel")
    return p.parse_args()

def load_planets(path: Path):
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        planets = []
        for row in reader:
            pid = int(row["id"])
            status = (row.get("status") or "normal").strip().lower()
            planets.append({"id": pid, "status": status})
        if not planets:
            raise ValueError("No planets found in planet.csv")
        return planets

def load_vessels(path: Path):
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        vessels = []
        for row in reader:
            vessels.append({
                "id": int(row["id"]),
                "name": row.get("name", "").strip(),
                "captain": row.get("captain", "").strip(),
                "type_raw": row.get("type", "").strip().lower(),
                "flag": int(row.get("flag", 0)),
            })
        if not vessels:
            raise ValueError("No vessels found in vessel.csv")
        return vessels

def canonical_type(type_raw: str) -> str:
    type_raw = (type_raw or "").lower()
    for canon, tokens in TYPE_MAP.items():
        for t in tokens:
            if t in type_raw:
                return canon
    return "unknown"

def pick_planet_weighted(planets, exclude_id=None):
    items = []
    weights = []
    for p in planets:
        if exclude_id is not None and p["id"] == exclude_id:
            continue
        items.append(p["id"])
        weights.append(PLANET_STATUS_WEIGHTS.get(p["status"], 0.3))
    # Weighted random choice
    total = sum(weights)
    r = random.uniform(0, total)
    acc = 0.0
    for item, w in zip(items, weights):
        acc += w
        if r <= acc:
            return item
    return items[-1]

def sample_int_hours(lo, hi):
    return random.randint(int(lo), int(max(lo, hi)))

def random_datetime_in_june():
    day = random.randint(JUNE_DAY_MIN, JUNE_DAY_MAX)
    hour = random.randint(0, 23)
    minute = random.randint(0, 59)
    second = random.randint(0, 59)
    return datetime(JUNE_YEAR, JUNE_MONTH, day, hour, minute, second, tzinfo=timezone.utc)

def ensure_not_same_port(prev_port, candidate_port):
    # small helper to avoid immediate repeated port where possible
    if prev_port is None:
        return candidate_port
    if candidate_port == prev_port:
        return None
    return candidate_port

def generate_logs(planets, vessels, out_path: Path, seed=None, max_prev=8):
    if seed is not None:
        random.seed(seed)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    rows = []
    log_id = 1

    # Precompute planet ids for fallback choices
    planet_ids = [p["id"] for p in planets]

    for v in vessels:
        # derive profile
        canon = canonical_type(v["type_raw"])
        profile = TYPE_PROFILES.get(canon, DEFAULT_PROFILE)

        prev_min, prev_max = profile["prev_range"]
        # Respect the global hard cap
        prev_max = min(prev_max, max_prev)
        if prev_max < prev_min:
            prev_max = prev_min
        prev_count = random.randint(prev_min, prev_max)

        # Final arrival in June 2973
        final_arrival_dt = random_datetime_in_june()
        stay_lo, stay_hi = profile["stay_hours"]
        final_stay_h = sample_int_hours(stay_lo, stay_hi)
        final_departure_dt = final_arrival_dt + timedelta(hours=final_stay_h)

        # pick final port with bias towards flag
        if random.random() < FINAL_PORT_FLAG_BIAS and v["flag"] in planet_ids:
            final_port = v["flag"]
        else:
            final_port = pick_planet_weighted(planets)

        # Build previous stops backwards from the final arrival
        next_arrival = final_arrival_dt
        next_port = final_port

        # Generate previous stops in reverse chronological order
        for i in range(prev_count):
            travel_lo, travel_hi = profile["travel_hours"]
            stay_lo, stay_hi = profile["stay_hours"]

            travel_h = random.uniform(travel_lo, travel_hi)
            # previous departure is next_arrival - travel_time
            prev_departure_dt = next_arrival - timedelta(hours=travel_h)

            # stay duration at previous port
            prev_stay_h = random.uniform(stay_lo * 0.5, stay_hi)  # allow shorter stays sometimes
            prev_arrival_dt = prev_departure_dt - timedelta(hours=prev_stay_h)

            # choose a port for this previous stop (avoid immediate repetition where possible)
            candidate = pick_planet_weighted(planets, exclude_id=next_port)
            if candidate is None:
                # fallback to any planet
                candidate = random.choice(planet_ids)

            # append row
            rows.append({
                "id": log_id,
                "port": candidate,
                "arrival": int(prev_arrival_dt.timestamp()),
                "departure": int(prev_departure_dt.timestamp()),
                "vessel": v["id"],
            })
            log_id += 1

            # set up for next previous
            next_arrival = prev_arrival_dt
            next_port = candidate

        # Finally append the June 2973 arrival (most recent)
        rows.append({
            "id": log_id,
            "port": final_port,
            "arrival": int(final_arrival_dt.timestamp()),
            "departure": int(final_departure_dt.timestamp()),
            "vessel": v["id"],
        })
        log_id += 1

    # Optionally shuffle rows to avoid strict vessel-grouping (keeps CSV varied).
    # Keep chronological ordering per vessel would be broken by shuffle; we will not shuffle
    # to preserve increasing chronological order of the appended rows (older entries first,
    # final arrival last for each vessel). If you want shuffled output, call random.shuffle(rows).

    # Write CSV
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["id", "port", "arrival", "departure", "vessel"])
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    print(f"Wrote {len(rows)} log rows to {out_path} (for {len(vessels)} vessels).")

def main():
    args = parse_args()
    if args.seed is not None:
        random.seed(args.seed)

    planets = load_planets(args.planets)
    vessels = load_vessels(args.vessels)

    generate_logs(planets, vessels, args.out, seed=args.seed, max_prev=args.max_prev)

if __name__ == "__main__":
    main()
