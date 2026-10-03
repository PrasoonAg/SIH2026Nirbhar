"""
nirbhar/industrial/refinery.py
==============================
Multi-Period Sovereign Refinery Planning LP/MILP/QP Generator for MRPL (§6.11).
Models crude distillation (CDU), hydrotreating, product blending, inventory, and logistics.

Problem Classes:
  - LP   : Standard continuous multi-period refinery linear program
  - MILP : Unit startup/shutdown binary states and minimum run limits
  - QP   : Non-linear product quality giveaway and blending penalties (0.5 x^T Q x)

Data Source: SYNTHETIC operational data (per SIH26119 problem description).
"""

from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Optional, List, Dict, Tuple
import numpy as np

from nirbhar.io.model import Model, INF, build_csr, build_csc


@dataclass
class CrudeGrade:
    name: str
    price: float        # $/bbl
    avail_kbd: float    # max kbd available per period
    sulfur_pct: float   # % sulfur
    yields: list[float] # fractions: [LPG, Naphtha, Gasoline, ATF, Diesel, FuelOil]


# Seeded synthetic crude slate & refinery configuration
CRUDE_SLATE: list[CrudeGrade] = [
    CrudeGrade("Arab_Light",    82.0, 120.0, 1.8, [0.04, 0.12, 0.18, 0.08, 0.32, 0.26]),
    CrudeGrade("Arab_Heavy",    76.0,  80.0, 2.9, [0.02, 0.09, 0.15, 0.07, 0.30, 0.37]),
    CrudeGrade("Basra_Light",   80.0,  60.0, 2.1, [0.03, 0.11, 0.17, 0.08, 0.31, 0.30]),
    CrudeGrade("Iranian_Light", 78.5,  50.0, 1.5, [0.04, 0.13, 0.19, 0.09, 0.33, 0.22]),
    CrudeGrade("Kuwait",        79.0,  70.0, 2.6, [0.03, 0.10, 0.16, 0.07, 0.31, 0.33]),
    CrudeGrade("Murban",        88.0,  40.0, 0.8, [0.05, 0.15, 0.21, 0.10, 0.34, 0.15]),
]

PRODUCTS: list[str] = ["LPG", "Naphtha", "Gasoline", "ATF", "Diesel", "FuelOil"]

PRODUCT_PRICES: dict[str, float] = {
    "LPG": 55.0, "Naphtha": 75.0, "Gasoline": 95.0,
    "ATF": 100.0, "Diesel": 98.0, "FuelOil": 45.0,
}

DEMAND_MIN: dict[str, float] = {
    "LPG": 5.0, "Naphtha": 10.0, "Gasoline": 20.0,
    "ATF": 8.0, "Diesel": 35.0, "FuelOil": 10.0,
}

DEMAND_MAX: dict[str, float] = {
    "LPG": 15.0, "Naphtha": 30.0, "Gasoline": 50.0,
    "ATF": 20.0, "Diesel": 80.0, "FuelOil": 40.0,
}

TANK_CAPACITY: dict[str, float] = {
    "LPG": 20.0, "Naphtha": 50.0, "Gasoline": 80.0,
    "ATF": 30.0, "Diesel": 100.0, "FuelOil": 60.0,
}

INITIAL_INVENTORY: dict[str, float] = {
    "LPG": 8.0, "Naphtha": 20.0, "Gasoline": 30.0,
    "ATF": 10.0, "Diesel": 40.0, "FuelOil": 20.0,
}


def build_refinery_model(
    periods: int = 4,
    problem_class: str = "LP",       # "LP" | "MILP" | "QP"
    scenario: str = "baseline",      # "baseline" | "tight-sulfur" | "crude-shock" | "diesel-surge"
    cdu_capacity_kbd: float = 200.0,
    sulfur_limit_pct: float = 2.0,
) -> Model:
    """
    Generate an immutable NIRBHAR Model for Multi-Period Refinery Planning.
    """
    n_crudes = len(CRUDE_SLATE)
    n_prods = len(PRODUCTS)

    # Scenario parameter adjustments
    crude_multiplier = 0.75 if scenario == "crude-shock" else 1.0
    sulfur_cap = 1.3 if scenario == "tight-sulfur" else sulfur_limit_pct
    diesel_price_boost = 1.3 if scenario == "diesel-surge" else 1.0

    # Variable counts:
    # Per period t:
    #   - crude_proc[c, t]  (n_crudes)
    #   - sales[p, t]       (n_prods)
    #   - inv[p, t]         (n_prods)
    # If MILP:
    #   - cdu_active[t]     (1 binary per period)
    # Total cols:
    vars_per_period = n_crudes + 2 * n_prods + (1 if problem_class == "MILP" else 0)
    ncols = periods * vars_per_period

    col_names: list[str] = []
    col_lo = np.zeros(ncols, dtype=np.float64)
    col_hi = np.full(ncols, INF, dtype=np.float64)
    c_obj = np.zeros(ncols, dtype=np.float64)  # Minimization: cost - revenue
    integrality = np.zeros(ncols, dtype=np.int8)

    col_idx = 0
    # Map variable names to column indices
    var_map: dict[str, int] = {}

    for t in range(periods):
        # 1. Crude procurement vars
        for c_idx, crude in enumerate(CRUDE_SLATE):
            name = f"crude_{crude.name}_t{t+1}"
            col_names.append(name)
            var_map[name] = col_idx
            col_lo[col_idx] = 0.0
            col_hi[col_idx] = crude.avail_kbd
            c_obj[col_idx] = crude.price * crude_multiplier  # Crude cost
            col_idx += 1

        # 2. Product sales vars
        for p_idx, prod in enumerate(PRODUCTS):
            name = f"sales_{prod}_t{t+1}"
            col_names.append(name)
            var_map[name] = col_idx
            col_lo[col_idx] = DEMAND_MIN[prod] * (1.25 if prod == "Diesel" and scenario == "diesel-surge" else 1.0)
            col_hi[col_idx] = DEMAND_MAX[prod]
            price = PRODUCT_PRICES[prod] * (diesel_price_boost if prod == "Diesel" else 1.0)
            c_obj[col_idx] = -price  # Revenue (negative cost)
            col_idx += 1

        # 3. Product inventory vars
        for p_idx, prod in enumerate(PRODUCTS):
            name = f"inv_{prod}_t{t+1}"
            col_names.append(name)
            var_map[name] = col_idx
            col_lo[col_idx] = 0.0
            col_hi[col_idx] = TANK_CAPACITY[prod]
            c_obj[col_idx] = 1.5  # Inventory holding cost ($1.5/bbl/period)
            col_idx += 1

        # 4. Optional MILP binary operational state
        if problem_class == "MILP":
            name = f"cdu_on_t{t+1}"
            col_names.append(name)
            var_map[name] = col_idx
            col_lo[col_idx] = 0.0
            col_hi[col_idx] = 1.0
            integrality[col_idx] = 2  # Binary
            c_obj[col_idx] = 5000.0   # Fixed operating/startup cost per period
            col_idx += 1

    # Constraints:
    # Per period t:
    #   1. CDU Throughput capacity: sum(crude_proc) <= cdu_capacity_kbd  (or <= cap * cdu_on if MILP)
    #   2. Min CDU run (if MILP): sum(crude_proc) >= min_run * cdu_on
    #   3. Blended Sulfur spec: sum(crude * sulfur) <= sulfur_cap * sum(crude)
    #      <=> sum( (sulfur - sulfur_cap) * crude ) <= 0
    #   4. Inventory balance per product p:
    #      inv_{t} - inv_{t-1} - sum(yield * crude_t) + sales_t = 0
    rows_coo: list[int] = []
    cols_coo: list[int] = []
    vals_coo: list[float] = []
    row_names: list[str] = []
    row_lo: list[float] = []
    row_hi: list[float] = []

    curr_row = 0

    for t in range(periods):
        # 1. CDU throughput
        row_name = f"cdu_cap_t{t+1}"
        row_names.append(row_name)
        row_lo.append(-INF)
        if problem_class == "MILP":
            # sum(crude) - cap * cdu_on <= 0
            row_hi.append(0.0)
            for crude in CRUDE_SLATE:
                rows_coo.append(curr_row)
                cols_coo.append(var_map[f"crude_{crude.name}_t{t+1}"])
                vals_coo.append(1.0)
            rows_coo.append(curr_row)
            cols_coo.append(var_map[f"cdu_on_t{t+1}"])
            vals_coo.append(-cdu_capacity_kbd)
        else:
            row_hi.append(cdu_capacity_kbd)
            for crude in CRUDE_SLATE:
                rows_coo.append(curr_row)
                cols_coo.append(var_map[f"crude_{crude.name}_t{t+1}"])
                vals_coo.append(1.0)
        curr_row += 1

        # 2. Min run if MILP
        if problem_class == "MILP":
            row_name = f"cdu_min_run_t{t+1}"
            row_names.append(row_name)
            row_lo.append(0.0)
            row_hi.append(INF)
            # sum(crude) - 50.0 * cdu_on >= 0
            for crude in CRUDE_SLATE:
                rows_coo.append(curr_row)
                cols_coo.append(var_map[f"crude_{crude.name}_t{t+1}"])
                vals_coo.append(1.0)
            rows_coo.append(curr_row)
            cols_coo.append(var_map[f"cdu_on_t{t+1}"])
            vals_coo.append(-50.0)
            curr_row += 1

        # 3. Sulfur specification
        row_name = f"sulfur_limit_t{t+1}"
        row_names.append(row_name)
        row_lo.append(-INF)
        row_hi.append(0.0)
        for crude in CRUDE_SLATE:
            coeff = crude.sulfur_pct - sulfur_cap
            rows_coo.append(curr_row)
            cols_coo.append(var_map[f"crude_{crude.name}_t{t+1}"])
            vals_coo.append(coeff)
        curr_row += 1

        # 4. Product inventory balance
        for p_idx, prod in enumerate(PRODUCTS):
            row_name = f"balance_{prod}_t{t+1}"
            row_names.append(row_name)

            # inv_t - inv_{t-1} - sum(yield * crude_t) + sales_t = 0
            # If t=0, inv_{t-1} is initial_inventory
            rhs_const = float(INITIAL_INVENTORY[prod]) if t == 0 else 0.0
            row_lo.append(rhs_const)
            row_hi.append(rhs_const)

            # + inv_t
            rows_coo.append(curr_row)
            cols_coo.append(var_map[f"inv_{prod}_t{t+1}"])
            vals_coo.append(1.0)

            # - inv_{t-1}
            if t > 0:
                rows_coo.append(curr_row)
                cols_coo.append(var_map[f"inv_{prod}_t{t}"])
                vals_coo.append(-1.0)

            # + sales_t
            rows_coo.append(curr_row)
            cols_coo.append(var_map[f"sales_{prod}_t{t+1}"])
            vals_coo.append(1.0)

            # - sum(yield * crude_t)
            for c_idx, crude in enumerate(CRUDE_SLATE):
                yield_frac = crude.yields[p_idx]
                rows_coo.append(curr_row)
                cols_coo.append(var_map[f"crude_{crude.name}_t{t+1}"])
                vals_coo.append(-yield_frac)

            curr_row += 1

    nrows = curr_row
    A_csr = build_csr(rows_coo, cols_coo, vals_coo, nrows, ncols)
    A_csc = build_csc(rows_coo, cols_coo, vals_coo, nrows, ncols)

    # Optional Quadratic Objective (QP)
    Q_upper = None
    if problem_class == "QP":
        Q_upper = {}
        # Add small convex quadratic penalty on inventory storage and sales to penalize fluctuation
        for t in range(periods):
            for prod in PRODUCTS:
                inv_c = var_map[f"inv_{prod}_t{t+1}"]
                Q_upper[(inv_c, inv_c)] = 0.05
                sales_c = var_map[f"sales_{prod}_t{t+1}"]
                Q_upper[(sales_c, sales_c)] = 0.02

    return Model(
        nrows=nrows,
        ncols=ncols,
        c=c_obj,
        obj_const=0.0,
        sense="min",
        A_csr=A_csr,
        A_csc=A_csc,
        row_lo=np.array(row_lo, dtype=np.float64),
        row_hi=np.array(row_hi, dtype=np.float64),
        col_lo=col_lo,
        col_hi=col_hi,
        integrality=integrality,
        Q_upper=Q_upper,
        row_names=tuple(row_names),
        col_names=tuple(col_names),
        obj_name=f"MRPL_Refinery_{problem_class}_{scenario}",
        sha256="",
        source_path=None,
    )
