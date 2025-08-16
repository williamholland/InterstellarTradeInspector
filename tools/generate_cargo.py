# tools/generate_cargo.py
"""
Generate a cargo.csv from an existing vessels CSV.

Reads:
  - data/vessel.csv   (id,name,captain,type,flag)

Writes:
  - data/cargo.csv    (id,description,category,weight,hazardous,consignee,consignor,vessel)

Design notes (thought-through):
  - Number of cargo rows per vessel depends on vessel type (tankers have few heavy loads,
    container haulers have many containers, passenger liners have modest numbers).
  - Category selection is biased by vessel role to produce realistic manifests.
  - Each category has a set of description templates and a sensible per-unit weight range.
  - Hazardous flag is tightly correlated with category (e.g. "chemicals", "explosives",
    "radioactive" are almost always hazardous).
  - Consignee/consignor are chosen from a pool of company or person names to look realistic.
  - No fixed total number of rows — output scales with vessels.csv. Use --scale to shrink
    or expand generated manifests.
Usage:
    python tools/generate_cargo.py --seed 7 --scale 1.0 --out data/cargo.csv
"""

from pathlib import Path
import csv
import random
import argparse

VESSEL_CSV = Path("data/vessel.csv")
OUT_CSV = Path("data/cargo.csv")

# Map rough vessel types (substring matching) to canonical types and cargo profiles
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

# How many cargo items per vessel (min, max) — these are "manifest lines"
VESSEL_CARGO_COUNTS = {
    "passenger liner": (8, 30),
    "interstellar shuttle": (2, 10),
    "private yacht": (1, 8),
    "bulk freighter": (10, 80),
    "container hauler": (20, 200),
    "tanker": (1, 6),
    "fast courier": (3, 18),
    "research vessel": (5, 30),
    "mining barge": (8, 60),
    "patrol corvette": (2, 10),
    "medical relief ship": (6, 40),
    "customs cutter": (2, 12),
    "unknown": (2, 12),
}

# Category definitions:
# - unit_weight_range: typical weight per "unit" referenced in description (kg)
# - qty_range: how many units are represented by a manifest line
# - hazard_prob: base probability (0..1) that this manifest line is hazardous
# - always_hazard: if True, hazardous=1 deterministically
# - templates: templates for description. Use {qty} and {unit_label} and {item}
CATEGORY_DEFS = {
    "Food": {
        "unit_weight_range": (0.5, 20.0),
        "qty_range": (1, 12),
        "hazard_prob": 0.01,
        "always_hazard": False,
        "templates": [
            "{qty} crates of Cryo-fruit",
            "{qty} cartons of Canned Rations",
            "{qty} kegs of Fermented Nectar",
            "{qty} pallets of Hydroponic Produce",
            "{qty} drums of Bottled Water"
        ],
    },
    "Alcohol": {
        "unit_weight_range": (0.5, 30.0),
        "qty_range": (1, 8),
        "hazard_prob": 0.01,
        "always_hazard": False,
        "templates": [
            "{qty} cases of Distilled Spirits",
            "{qty} barrels of Aged Fortified Wine",
            "{qty} crates of Galactic Beer",
            "{qty} bottles of Vintage Liqueur"
        ],
    },
    "Electronics": {
        "unit_weight_range": (0.2, 50.0),
        "qty_range": (1, 20),
        "hazard_prob": 0.01,
        "always_hazard": False,
        "templates": [
            "{qty} crates of Comms Arrays",
            "{qty} sealed boxes of Navigation Chips",
            "{qty} pallets of Consumer Electronics",
            "{qty} modules of Sensor Suites"
        ],
    },
    "Medical": {
        "unit_weight_range": (0.05, 20.0),
        "qty_range": (1, 30),
        "hazard_prob": 0.03,
        "always_hazard": False,
        "templates": [
            "{qty} boxes of Vaccine Vials",
            "{qty} crates of Surgical Kits",
            "{qty} cases of Medical Consumables",
            "{qty} sealed containers of Sterile Dressings"
        ],
    },
    "Luxury": {
        "unit_weight_range": (0.1, 80.0),
        "qty_range": (1, 12),
        "hazard_prob": 0.01,
        "always_hazard": False,
        "templates": [
            "{qty} crates of Luxury Textiles",
            "{qty} crates of Gemware",
            "{qty} packages of Designer Goods",
            "{qty} boxes of Antique Instruments"
        ],
    },
    "Machinery": {
        "unit_weight_range": (10.0, 5000.0),
        "qty_range": (1, 6),
        "hazard_prob": 0.02,
        "always_hazard": False,
        "templates": [
            "{qty} heavy crates of Engine Components",
            "{qty} pallets of Industrial Pumps",
            "{qty} containers of Precision Gears",
            "{qty} crates of Manufacturing Rigs"
        ],
    },
    "Spare Parts": {
        "unit_weight_range": (0.5, 300.0),
        "qty_range": (1, 40),
        "hazard_prob": 0.01,
        "always_hazard": False,
        "templates": [
            "{qty} boxes of Replacement Valves",
            "{qty} crates of Structural Fasteners",
            "{qty} pallets of Spare Assemblies",
            "{qty} bins of Electronics Spares"
        ],
    },
    "Chemicals": {
        "unit_weight_range": (5.0, 4000.0),
        "qty_range": (1, 12),
        "hazard_prob": 0.9,
        "always_hazard": False,
        "templates": [
            "{qty} drums of Industrial Solvent",
            "{qty} barrels of Reactive Compound",
            "{qty} containers of Agricultural Pesticide",
            "{qty} drums of Cryo-reagent"
        ],
    },
    "Explosives": {
        "unit_weight_range": (1.0, 200.0),
        "qty_range": (1, 6),
        "hazard_prob": 1.0,
        "always_hazard": True,
        "templates": [
            "{qty} crates of Demolition Charges",
            "{qty} sealed drums of Propellant",
            "{qty} cases of Pyrotechnic Rounds"
        ],
    },
    "Radioactive": {
        "unit_weight_range": (0.1, 200.0),
        "qty_range": (1, 4),
        "hazard_prob": 1.0,
        "always_hazard": True,
        "templates": [
            "{qty} shielded containers of Radioisotopes",
            "{qty} lead-lined crates of Reactor Pellets"
        ],
    },
    "Live Animals": {
        "unit_weight_range": (1.0, 1200.0),
        "qty_range": (1, 20),
        "hazard_prob": 0.05,
        "always_hazard": False,
        "templates": [
            "{qty} bio-cages of Migratory Herds",
            "{qty} crates of Domesticated Stock",
            "{qty} sealed terrariums of Exotic Fauna"
        ],
    },
    "Fuel": {
        "unit_weight_range": (500.0, 1_000_000.0),
        "qty_range": (1, 4),
        "hazard_prob": 0.95,
        "always_hazard": False,
        "templates": [
            "{qty} tank-containers of Refined Fuel",
            "{qty} drums of Cryo-fuel",
            "{qty} bulk tanks of Hydrogen Slurry"
        ],
    },
    "Raw Ore": {
        "unit_weight_range": (100.0, 50_000.0),
        "qty_range": (1, 12),
        "hazard_prob": 0.02,
        "always_hazard": False,
        "templates": [
            "{qty} pallets of Iron Ore",
            "{qty} bulk sacks of Rare Earths",
            "{qty} crates of Refined Ore"
        ],
    },
    "Weapons": {
        "unit_weight_range": (1.0, 600.0),
        "qty_range": (1, 8),
        "hazard_prob": 0.85,
        "always_hazard": False,
        "templates": [
            "{qty} crates of Military Hardware",
            "{qty} sealed crates of Ordinance",
            "{qty} pallets of Armament Components"
        ],
    },
}

# Per-vessel-type category weightings (for more realistic manifests)
# Keys are canonical vessel types; values are lists of (category, weight)
DEFAULT_CATEGORY_WEIGHTS = [
    ("Spare Parts", 0.10), ("Machinery", 0.12), ("Food", 0.10),
    ("Electronics", 0.08), ("Luxury", 0.05), ("Chemicals", 0.06),
    ("Alcohol", 0.04), ("Medical", 0.06), ("Raw Ore", 0.08),
    ("Fuel", 0.05), ("Weapons", 0.01), ("Explosives", 0.01),
    ("Live Animals", 0.04), ("Radioactive", 0.01)
]

CATEGORY_WEIGHTS_BY_TYPE = {
    "container hauler": [
        ("Spare Parts", 0.12), ("Machinery", 0.12), ("Electronics", 0.15),
        ("Food", 0.10), ("Luxury", 0.08), ("Alcohol", 0.06), ("Medical", 0.06),
        ("Raw Ore", 0.05), ("Weapons", 0.03), ("Chemicals", 0.06), ("Live Animals", 0.07)
    ],
    "bulk freighter": [
        ("Raw Ore", 0.50), ("Fuel", 0.15), ("Machinery", 0.10), ("Spare Parts", 0.07),
        ("Food", 0.08), ("Chemicals", 0.05), ("Live Animals", 0.05)
    ],
    "tanker": [
        ("Fuel", 0.70), ("Chemicals", 0.25), ("Spare Parts", 0.05)
    ],
    "passenger liner": [
        ("Luxury", 0.25), ("Food", 0.20), ("Electronics", 0.15), ("Medical", 0.10),
        ("Alcohol", 0.10), ("Spare Parts", 0.10), ("Live Animals", 0.05)
    ],
    "private yacht": [
        ("Luxury", 0.45), ("Alcohol", 0.20), ("Electronics", 0.15), ("Spare Parts", 0.10), ("Food", 0.10)
    ],
    "fast courier": [
        ("Electronics", 0.30), ("Medical", 0.20), ("Luxury", 0.15), ("Spare Parts", 0.15), ("Food", 0.20)
    ],
    "mining barge": [
        ("Raw Ore", 0.75), ("Spare Parts", 0.10), ("Machinery", 0.10), ("Fuel", 0.05)
    ],
    "research vessel": [
        ("Medical", 0.15), ("Electronics", 0.25), ("Chemicals", 0.20), ("Spare Parts", 0.20), ("Luxury", 0.05)
    ],
    "customs cutter": [
        ("Spare Parts", 0.30), ("Electronics", 0.25), ("Medical", 0.20), ("Food", 0.25)
    ],
}

# Company and person pools for consignee/consignor generation
COMPANIES = [
    "AstraCorp Logistics", "Nova Traders", "Zenith Freight", "Orbital Freight Ltd",
    "Sol Systems Trading", "Horizon Shipping", "Pioneer Exporters", "Lumen Imports",
    "Aurora Holdings", "Mercury Trade Consortium", "Polaris Carriers", "Echelon Shipping"
]

FIRST_NAMES = [
    "Alex", "Samira", "Diego", "Mei", "Noah", "Aisha", "Karim", "Sofia", "Luca",
    "Yara", "Tariq", "Nina", "Jonas", "Ravi", "Leila", "Kaito", "Marta", "Omar",
    "Ibrahim", "Priya", "Ines", "Serge", "Dara", "Hana", "Arman", "Zoe"
]
SURNAMES = [
    "Okoye", "Fernandez", "Singh", "Johansson", "Khan", "Miller", "Garcia", "Chen",
    "Haddad", "Nakamura", "Silva", "Novak", "Rossi", "Patel", "Dubois", "Iversen"
]


def parse_args():
    p = argparse.ArgumentParser(description="Generate cargo.csv using vessel.csv.")
    p.add_argument("--vessels", type=Path, default=VESSEL_CSV, help="Path to vessel.csv")
    p.add_argument("--out", type=Path, default=OUT_CSV, help="Output path for cargo.csv")
    p.add_argument("--seed", type=int, default=None, help="Random seed for reproducibility")
    p.add_argument("--scale", type=float, default=1.0, help="Scale overall cargo counts (e.g., 0.5 halves lines)")
    return p.parse_args()


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
        raise ValueError("No vessels found in vessels CSV")
    return vessels


def canonical_type(type_raw: str) -> str:
    type_raw = (type_raw or "").lower()
    for canon, tokens in TYPE_MAP.items():
        for t in tokens:
            if t in type_raw:
                return canon
    return "unknown"


def weighted_choice(items_with_weights):
    total = sum(w for _, w in items_with_weights)
    r = random.uniform(0, total)
    acc = 0.0
    for it, w in items_with_weights:
        acc += w
        if r <= acc:
            return it
    return items_with_weights[-1][0]


def pick_category_for_vessel(canon_type):
    if canon_type in CATEGORY_WEIGHTS_BY_TYPE:
        weights = CATEGORY_WEIGHTS_BY_TYPE[canon_type]
    else:
        weights = DEFAULT_CATEGORY_WEIGHTS
    # convert to list of (category, weight)
    return weighted_choice(weights)


def choose_quantity_for_category(cat_def):
    lo, hi = cat_def["qty_range"]
    return random.randint(lo, max(lo, hi))


def choose_unit_weight_for_category(cat_def):
    lo, hi = cat_def["unit_weight_range"]
    return random.uniform(lo, hi)


def make_description(template, qty):
    return template.format(qty=qty)


def make_consignee():
    # 60% company, 40% individual
    if random.random() < 0.6:
        return random.choice(COMPANIES)
    else:
        return f"{random.choice(FIRST_NAMES)} {random.choice(SURNAMES)}"


def make_consignor():
    # 50% company, 50% individual
    if random.random() < 0.5:
        return random.choice(COMPANIES)
    else:
        return f"{random.choice(FIRST_NAMES)} {random.choice(SURNAMES)}"


def generate_cargo(vessels, out_path: Path, seed=None, scale: float = 1.0):
    if seed is not None:
        random.seed(seed)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    cargo_rows = []
    cid = 1

    for v in vessels:
        canon = canonical_type(v["type_raw"])
        lo, hi = VESSEL_CARGO_COUNTS.get(canon, VESSEL_CARGO_COUNTS["unknown"])
        # scale the counts but ensure at least 1 line for every vessel
        lo_s = max(1, int(round(lo * scale)))
        hi_s = max(lo_s, int(round(hi * scale)))
        n_items = random.randint(lo_s, hi_s)

        for _ in range(n_items):
            category = pick_category_for_vessel(canon)
            cat_def = CATEGORY_DEFS.get(category, None)
            if cat_def is None:
                # fallback
                category = "Spare Parts"
                cat_def = CATEGORY_DEFS[category]

            qty = choose_quantity_for_category(cat_def)
            unit_w = choose_unit_weight_for_category(cat_def)
            # weight is qty * unit weight, round to 3 decimals
            weight = round(qty * unit_w, 3)

            # description template selection
            template = random.choice(cat_def["templates"])
            description = make_description(template, qty)

            # hazardous decision
            if cat_def.get("always_hazard", False):
                hazardous = 1
            else:
                hazardous = 1 if random.random() < cat_def.get("hazard_prob", 0.0) else 0

            consignee = make_consignee()
            consignor = make_consignor()

            cargo_rows.append({
                "id": cid,
                "description": description,
                "category": category,
                "weight": weight,
                "hazardous": hazardous,
                "consignee": consignee,
                "consignor": consignor,
                "vessel": v["id"],
            })
            cid += 1

    # write CSV
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["id", "description", "category", "weight", "hazardous", "consignee", "consignor", "vessel"])
        writer.writeheader()
        writer.writerows(cargo_rows)

    print(f"Wrote {len(cargo_rows)} cargo rows to {out_path} for {len(vessels)} vessels.")


def main():
    args = parse_args()
    if args.seed is not None:
        random.seed(args.seed)
    vessels = load_vessels(args.vessels)
    generate_cargo(vessels, args.out, seed=args.seed, scale=args.scale)


if __name__ == "__main__":
    main()
