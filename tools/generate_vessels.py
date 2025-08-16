# tools/generate_vessels.py
"""
Generate a vessels.csv from an existing planets CSV.

Reads:   data/planet.csv  (columns: id,name,mass,status)
Writes:  data/vessel.csv  (columns: id,name,captain,type,flag)

Design:
- Each vessel's 'flag' is a valid Planet id from planet.csv.
- Flags are sampled with status-aware weights so most ships fly 'normal' flags,
  but some originate from frontier/restricted worlds for variety.
- Vessel names are unique and varied (prefix + evocative name with optional numeral).
- Captain names are randomly generated from international-style name lists.
- Types are sampled from a weighted distribution of plausible roles.

Usage:
    python tools/generate_vessels.py --count 200 --seed 7
"""

from pathlib import Path
import csv
import random
import argparse

PLANET_CSV = Path("data/planet.csv")
VESSEL_CSV = Path("data/vessel.csv")

# Weighting for choosing a planet as a flag, based on its status
STATUS_FLAG_WEIGHTS = {
    "normal": 1.00,
    "frontier": 0.25,
    "restricted": 0.20,
    "quarantine": 0.10,
    "embargo": 0.08,
}

VESSEL_TYPES = [
    ("bulk freighter", 0.18),
    ("container hauler", 0.16),
    ("tanker", 0.12),
    ("passenger liner", 0.08),
    ("interstellar shuttle", 0.08),
    ("fast courier", 0.08),
    ("research vessel", 0.06),
    ("mining barge", 0.06),
    ("patrol corvette", 0.05),
    ("private yacht", 0.05),
    ("medical relief ship", 0.04),
    ("spice clipper", 0.04),
]

# Name parts for vessels
PREFIXES = ["SS", "MV", "CSV", "TSS", "HSS", "RV", "BCV"]
ADJECTIVES = [
    "Azure", "Crimson", "Obsidian", "Amber", "Silent", "Vigilant", "Radiant",
    "Stellar", "Drifting", "Iron", "Golden", "Silver", "Nebular", "Quantum",
    "Luminous", "Wayfarer", "Eclipse", "Solar", "Aether", "Celestial",
    "Cutty",
]
NOUNS = [
    "Nomad", "Kite", "Dawn", "Paradox", "Harbinger", "Serpent", "Pioneer",
    "Voyager", "Courier", "Beacon", "Comet", "Pilgrim", "Anchor", "Caravel",
    "Skylark", "Prospector", "Mariner", "Venture", "Tempest", "Sparrow", "Sark"
]
ROMAN = ["", " II", " III", " IV", " V"]

# International-flavoured names (plain, no titles)
FIRST_NAMES = [
    "Alex", "Samira", "Diego", "Mei", "Noah", "Aisha", "Karim", "Sofia", "Luca",
    "Yara", "Tariq", "Nina", "Jonas", "Ravi", "Leila", "Kaito", "Marta", "Omar",
    "Ibrahim", "Priya", "Ines", "Serge", "Dara", "Han", "Arman", "Zoe", "Nikolai",
    "Tess", "Amir", "Chioma", "Eli", "Mina", "Mateo", "Anika", "Farid", "Rosa"
    "Will",
]
SURNAMES = [
    "Okoye", "Fernandez", "Singh", "Johansson", "Khan", "Miller", "Garcia", "Chen",
    "Haddad", "Nakamura", "Silva", "Novak", "Rossi", "Patel", "Dubois", "Iversen",
    "Kim", "Hussein", "Santos", "Petrova", "Kowalski", "Hernandez", "Abebe",
    "Yamamoto", "Adebayo", "Popov", "Carter", "Moreau", "Gonzalez", "Li"
    "Nguyen", "Holland", "Nguyen Le", "Tram", "Ho",
]

def parse_args():
    p = argparse.ArgumentParser(description="Generate vessel.csv using planet.csv as flags.")
    p.add_argument("--count", type=int, default=2000, help="Number of vessels to generate")
    p.add_argument("--seed", type=int, default=None, help="Random seed for reproducibility")
    p.add_argument("--planet-csv", type=Path, default=PLANET_CSV, help="Path to planet.csv")
    p.add_argument("--out", type=Path, default=VESSEL_CSV, help="Output path for vessel.csv")
    return p.parse_args()

def load_planets(path: Path):
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        planets = []
        for row in reader:
            # Ensure required fields exist and are correctly typed
            pid = int(row["id"])
            status = (row.get("status") or "normal").strip().lower()
            planets.append({"id": pid, "status": status})
        if not planets:
            raise ValueError("No planets found in planet.csv")
        return planets

def weighted_choice(items, weights):
    total = sum(weights)
    r = random.uniform(0, total)
    acc = 0.0
    for item, w in zip(items, weights):
        acc += w
        if r <= acc:
            return item
    return items[-1]

def pick_flag(planets):
    weights = [STATUS_FLAG_WEIGHTS.get(p["status"], 0.1) for p in planets]
    chosen = weighted_choice(planets, weights)
    return chosen["id"]

def pick_type():
    return weighted_choice([t for t, _ in VESSEL_TYPES], [w for _, w in VESSEL_TYPES])

def make_vessel_name(existing: set):
    # 3 mixed patterns for variety
    pattern = random.random()
    if pattern < 0.45:
        name = f"{random.choice(PREFIXES)} {random.choice(ADJECTIVES)} {random.choice(NOUNS)}{random.choice(ROMAN)}"
    elif pattern < 0.80:
        name = f"{random.choice(ADJECTIVES)} {random.choice(NOUNS)}{random.choice(ROMAN)}"
    else:
        # Corporate / designation style
        name = f"{random.choice(PREFIXES)}-{random.randint(100, 9999)} {random.choice(NOUNS)}"

    # Ensure uniqueness
    if name in existing:
        # Add a numeric suffix until unique
        base = name
        idx = 2
        while name in existing:
            name = f"{base} ({idx})"
            idx += 1
    existing.add(name)
    return name

def make_captain_name():
    return f"{random.choice(FIRST_NAMES)} {random.choice(SURNAMES)}"

def generate_vessels(count, planets, out_path: Path, seed=None):
    if seed is not None:
        random.seed(seed)

    out_path.parent.mkdir(parents=True, exist_ok=True)

    names_seen = set()
    rows = []
    for vid in range(1, count + 1):
        vtype = pick_type()
        name = make_vessel_name(names_seen)
        captain = make_captain_name()
        flag = pick_flag(planets)

        rows.append({
            "id": vid,
            "name": name,
            "captain": captain,
            "type": vtype,
            "flag": flag,
        })

    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["id", "name", "captain", "type", "flag"])
        writer.writeheader()
        writer.writerows(rows)

def main():
    args = parse_args()
    planets = load_planets(args.planet_csv)
    generate_vessels(args.count, planets, args.out, seed=args.seed)

if __name__ == "__main__":
    main()
