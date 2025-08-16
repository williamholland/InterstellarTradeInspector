"""
Generate passenger.csv from planet.csv and vessel.csv.

Reads:
  - data/planet.csv   (id,name,mass,status)
  - data/vessel.csv   (id,name,captain,type,flag)

Writes:
  - data/passenger.csv (name,type,nationality,vessel)

Rules:
  - Every vessel’s captain is included as a passenger row with type='captain' and nationality set to the vessel’s flag.
  - Crew and passenger counts depend on vessel type; passenger liners always carry many passengers.
  - Nationalities are weighted towards 'normal' worlds; crew often share the flag world.

Usage:
    python tools/generate_passengers.py --seed 3
    python tools/generate_passengers.py --scale 0.5  # fewer people overall
"""

from pathlib import Path
import csv
import random
import argparse

PLANET_CSV = Path("data/planet.csv")
VESSEL_CSV = Path("data/vessel.csv")
PASSENGER_CSV = Path("data/passenger.csv")

# How many people per vessel type (ranges are inclusive)
# Counts are for additional people beyond the captain.
TYPE_PROFILE = {
    "passenger liner":      {"crew": (20, 40),  "passenger": (120, 400)},
    "interstellar shuttle": {"crew": (4, 10),   "passenger": (20, 80)},
    "private yacht":        {"crew": (4, 12),   "passenger": (0, 8)},
    "bulk freighter":       {"crew": (8, 20),   "passenger": (0, 6)},
    "container hauler":     {"crew": (8, 22),   "passenger": (0, 8)},
    "tanker":               {"crew": (6, 18),   "passenger": (0, 4)},
    "fast courier":         {"crew": (2, 6),    "passenger": (0, 4)},
    "research vessel":      {"crew": (12, 40),  "passenger": (0, 15)},
    "mining barge":         {"crew": (20, 60),  "passenger": (0, 10)},
    "patrol corvette":      {"crew": (15, 30),  "passenger": (0, 2)},
    "medical relief ship":  {"crew": (18, 60),  "passenger": (10, 120)},
    "customs cutter":       {"crew": (10, 20),  "passenger": (0, 2)},
}

# Weighted nationality sampling (more from normal worlds)
NATIONALITY_WEIGHTS = {
    "normal": 1.0,
    "frontier": 0.7,
    "restricted": 0.5,
    "quarantine": 0.25,
    "embargo": 0.2,
}

# Crew bias to be from the flag world
CREW_FLAG_PROB = 0.55

FIRST_NAMES = [
    "Alex", "Samira", "Diego", "Mei", "Noah", "Aisha", "Karim", "Sofia", "Luca",
    "Yara", "Tariq", "Nina", "Jonas", "Ravi", "Leila", "Kaito", "Marta", "Omar",
    "Ibrahim", "Priya", "Ines", "Serge", "Dara", "Hana", "Arman", "Zoe", "Nikolai",
    "Tess", "Amir", "Chioma", "Eli", "Mina", "Mateo", "Anika", "Farid", "Rosa",
    "Ethan", "Layla", "Hiro", "Amina", "Thiago", "Noura", "Jae", "Saanvi", "Ada",
]
SURNAMES = [
    "Okoye", "Fernandez", "Singh", "Johansson", "Khan", "Miller", "Garcia", "Chen",
    "Haddad", "Nakamura", "Silva", "Novak", "Rossi", "Patel", "Dubois", "Iversen",
    "Kim", "Hussein", "Santos", "Petrova", "Kowalski", "Hernandez", "Abebe",
    "Yamamoto", "Adebayo", "Popov", "Carter", "Moreau", "Gonzalez", "Li", "O'Neill",
    "Martinez", "Costa", "Becker", "Ivanov", "Abdullah", "Laurent", "Bauer",
]

def parse_args():
    p = argparse.ArgumentParser(description="Generate passenger.csv using planets and vessels.")
    p.add_argument("--planets", type=Path, default=PLANET_CSV, help="Path to planet.csv")
    p.add_argument("--vessels", type=Path, default=VESSEL_CSV, help="Path to vessel.csv")
    p.add_argument("--out", type=Path, default=PASSENGER_CSV, help="Output passenger.csv path")
    p.add_argument("--seed", type=int, default=None, help="Random seed")
    p.add_argument("--scale", type=float, default=1.0, help="Scale headcounts (e.g., 0.5 halves people)")
    return p.parse_args()

def load_planets(path: Path):
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        planets = []
        for row in reader:
            planets.append({
                "id": int(row["id"]),
                "status": (row.get("status") or "normal").strip().lower()
            })
    if not planets:
        raise ValueError("planet.csv is empty")
    return planets

def load_vessels(path: Path):
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        vessels = []
        for row in reader:
            vessels.append({
                "id": int(row["id"]),
                "name": row["name"],
                "captain": row["captain"],
                "type": row["type"].strip().lower(),
                "flag": int(row["flag"]),
            })
    if not vessels:
        raise ValueError("vessel.csv is empty")
    return vessels

def weighted_choice(items, weights):
    total = sum(weights)
    r = random.uniform(0, total)
    acc = 0.0
    for item, w in zip(items, weights):
        acc += w
        if r <= acc:
            return item
    return items[-1]

def pick_planet_id(planets):
    items = [p["id"] for p in planets]
    weights = [NATIONALITY_WEIGHTS.get(p["status"], 0.3) for p in planets]
    return weighted_choice(items, weights)

def unique_name(existing: set, preferred: str | None = None) -> str:
    if preferred and preferred not in existing:
        existing.add(preferred)
        return preferred
    # Try a few random combinations before suffixing
    for _ in range(50):
        name = f"{random.choice(FIRST_NAMES)} {random.choice(SURNAMES)}"
        if name not in existing:
            existing.add(name)
            return name
    # Suffix until unique
    idx = 2
    base = preferred or f"{random.choice(FIRST_NAMES)} {random.choice(SURNAMES)}"
    name = base
    while name in existing:
        name = f"{base} #{idx}"
        idx += 1
    existing.add(name)
    return name

def scaled_randint(lo: int, hi: int, scale: float) -> int:
    lo = max(0, int(round(lo * scale)))
    hi = max(lo, int(round(hi * scale)))
    return random.randint(lo, hi)

def generate_passengers(planets, vessels, out_path: Path, scale: float = 1.0):
    out_path.parent.mkdir(parents=True, exist_ok=True)

    names_seen = set()
    rows = []

    # Make a quick lookup for planets by id to get statuses if needed later
    planet_by_id = {p["id"]: p for p in planets}

    for v in vessels:
        vtype = v["type"]
        profile = TYPE_PROFILE.get(vtype, {"crew": (6, 18), "passenger": (0, 6)})

        # Captain
        captain_name = unique_name(names_seen, preferred=v["captain"])
        rows.append({
            "name": captain_name,
            "type": "captain",
            "nationality": v["flag"],  # captain registered to the flag world
            "vessel": v["id"],
        })

        # Crew
        crew_n = scaled_randint(*profile["crew"], scale)
        for _ in range(crew_n):
            name = unique_name(names_seen)
            # Many crew share flag nationality; otherwise weighted pick
            if random.random() < CREW_FLAG_PROB:
                nat = v["flag"]
            else:
                nat = pick_planet_id(planets)
            rows.append({
                "name": name,
                "type": "crew",
                "nationality": nat,
                "vessel": v["id"],
            })

        # Passengers
        pax_n = scaled_randint(*profile["passenger"], scale)
        for _ in range(pax_n):
            name = unique_name(names_seen)
            nat = pick_planet_id(planets)
            rows.append({
                "name": name,
                "type": "passenger",
                "nationality": nat,
                "vessel": v["id"],
            })

    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["name", "type", "nationality", "vessel"])
        writer.writeheader()
        writer.writerows(rows)

def main():
    args = parse_args()
    if args.seed is not None:
        random.seed(args.seed)
    planets = load_planets(args.planets)
    vessels = load_vessels(args.vessels)
    generate_passengers(planets, vessels, args.out, scale=args.scale)

if __name__ == "__main__":
    main()
