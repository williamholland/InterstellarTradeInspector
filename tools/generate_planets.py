# tools/generate_planets.py
"""
Generate a realistic-looking planet catalogue CSV for your game.

Writes: data/planet.csv
Schema: id,name,mass,status

- Names mix several believable schemes (catalogue designations, Greek letter + constellation,
  mythic/cultural names with Roman numerals, and 'New <City>' colonies).
- Mass values are in Earth masses (M⊕), sampled from weighted planet classes.
- Status is a weighted pick from: normal, quarantine, embargo, restricted, frontier.

Usage:
    python tools/generate_planets.py --count 60 --seed 42
"""

from pathlib import Path
import csv
import random
import argparse

OUT_PATH = Path("data/planet.csv")

STATUSES = [
    ("normal", 0.78),
    ("quarantine", 0.08),
    ("embargo", 0.06),
    ("restricted", 0.05),
    ("frontier", 0.03),
]

GREEK = [
    "Alpha", "Beta", "Gamma", "Delta", "Epsilon", "Zeta", "Eta", "Theta",
    "Iota", "Kappa", "Lambda", "Mu", "Nu", "Xi", "Omicron", "Pi", "Rho",
    "Sigma", "Tau", "Upsilon", "Phi", "Chi", "Psi", "Omega"
]

CONSTELLATIONS = [
    "Andromedae", "Aquilae", "Arcturi", "Bootis", "Cancri", "Cygni", "Draconis",
    "Eridani", "Hydrae", "Leonis", "Lyrae", "Pegasi", "Persei", "Scorpii",
    "Serpentis", "Tauri", "Ursae Majoris", "Ursae Minoris", "Virginis"
]

CATALOG_PREFIX = ["HD", "HIP", "Gliese", "Kepler", "KIC", "BD", "TOI", "WASP", "OGLE", "TRAPPIST"]

MYTHIC = [
    "Aurelia", "Hyperion", "Erebus", "Nyx", "Icarus", "Orpheus", "Ariadne",
    "Talos", "Janus", "Morpheus", "Tethys", "Rhea", "Helios", "Athena",
    "Hermes", "Selene", "Nereid", "Gaia", "Astraea", "Eos"
]

CITIES = [

    "Kyoto", "Liverpool", "Accra", "Valencia", "Kigali", "Reykjavik", "Odessa",
    "Quito", "Marseille", "Tunis", "Hanoi", "Lagos", "Auckland", "Perth",
    "Cork", "Zagreb", "Seville", "Osaka", "Cadiz", "Hanoi", "Danang", "Hue",
    "Tokyo", "Beijing", "Cairo", "Casablanca"

]

ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII"]

def weighted_choice(pairs):
    r = random.random()
    acc = 0.0
    for value, weight in pairs:
        acc += weight
        if r <= acc:
            return value
    return pairs[-1][0]

def pick_status():
    return weighted_choice(STATUSES)

def sample_mass():
    """
    Return a planet mass in Earth masses (M⊕) using weighted classes:
      - Dwarf (0.05–0.3): 5%
      - Terrestrial (0.3–2.0): 55%
      - Super-Earth (2–10): 25%
      - Mini-Neptune (10–20): 10%
      - Gas giant (50–318): 5%
    """
    r = random.random()
    if r < 0.05:
        return round(random.uniform(0.05, 0.30), 3)
    elif r < 0.60:
        return round(random.uniform(0.30, 2.00), 3)
    elif r < 0.85:
        return round(random.uniform(2.00, 10.00), 3)
    elif r < 0.95:
        return round(random.uniform(10.00, 20.00), 3)
    else:
        return round(random.uniform(50.0, 318.0), 3)

def name_catalogue():
    prefix = random.choice(CATALOG_PREFIX)
    number = random.randint(100, 99999)
    suffix = random.choice(list("bcdefgh"))
    return f"{prefix} {number} {suffix}"

def name_greek_constellation():
    return f"{random.choice(GREEK)} {random.choice(CONSTELLATIONS)} {random.choice(ROMAN)}"

def name_mythic_roman():
    return f"{random.choice(MYTHIC)} {random.choice(ROMAN)}"

def name_new_colony():
    return f"New {random.choice(CITIES)}"

def generate_name():
    """
    Blend patterns with weights:
      - Catalogue designation: 35%
      - Greek letter + constellation + Roman numeral: 30%
      - Mythic + Roman: 20%
      - New <City>: 15%
    """
    r = random.random()
    if r < 0.35:
        return name_catalogue()
    elif r < 0.65:
        return name_greek_constellation()
    elif r < 0.85:
        return name_mythic_roman()
    else:
        return name_new_colony()

def generate_planets(n, seed=None):
    if seed is not None:
        random.seed(seed)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    names_seen = set()
    rows = []

    for pid in range(1, n + 1):
        # Ensure unique names
        for _ in range(100):
            name = generate_name()
            if name not in names_seen:
                names_seen.add(name)
                break
        else:
            # Fallback if somehow 100 collisions
            name = f"{name_catalogue()}-{pid}"

        mass = sample_mass()
        status = pick_status()

        rows.append({
            "id": pid,
            "name": name,
            "mass": mass,
            "status": status
        })

    with OUT_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["id", "name", "mass", "status"])
        writer.writeheader()
        writer.writerows(rows)

def parse_args():
    p = argparse.ArgumentParser(description="Generate planet.csv with realistic names, masses, and statuses.")
    p.add_argument("--count", type=int, default=50, help="Number of planets to generate")
    p.add_argument("--seed", type=int, default=None, help="Random seed for reproducibility")
    return p.parse_args()

if __name__ == "__main__":
    args = parse_args()
    generate_planets(args.count, args.seed)
