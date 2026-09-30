/**
 * NIRBHAR — Sovereign Refinery Planning Demo Model Generator
 * 
 * Generates a realistic multi-period crude distillation, hydrotreating,
 * blending, and product logistics Linear Program (LP) based on synthetic refinery data.
 * 
 * Objectives:
 *   - Maximize Gross Refining Margin (GRM = Product Revenues - Crude Costs - Inventory Holding)
 * Constraints:
 *   - CDU distillation throughput capacity (kbd)
 *   - Blended crude sulfur content specification (%)
 *   - Multi-period product inventory balance: inv_{t} = inv_{t-1} + yields * crudes - sales_{t}
 *   - Finished product demand limits and tank capacities
 * 
 * Data source: SYNTHETIC (non-MRPL operational data) per KNOWN_LIMITS.md.
 */

import { ModelBuilder, INF, NEG_INF } from '../solver/io/model';
import type { Model } from '../solver/io/model';
import refinerySeed from '../data/reference/refinery.json';

export interface CrudeInfo {
  name: string;
  price: number;       // $/bbl
  avail_kbd: number;   // max kbd available
  sulfur_pct: number;  // % sulfur content
  yields: number[];    // fractions for LPG, Naphtha, Gasoline, ATF, Diesel, FuelOil
}

export interface RefineryScenario {
  id: string;
  name: string;
  description: string;
  sulfurLimitPct?: number;
  crudePriceMultiplier?: number;
  dieselPriceBoost?: number;
  cduCapacityMultiplier?: number;
}

export const REFINERY_SCENARIOS: RefineryScenario[] = [
  {
    id: 'baseline',
    name: 'Base Operating Plan',
    description: 'Standard 4-period seasonal schedule with average crude pricing and specifications.',
  },
  {
    id: 'tight-sulfur',
    name: 'Strict IMO 2026 Sulfur Cap',
    description: 'Environmental regulation reduces blended sulfur limit from 2.0% down to 1.3%. Favors sweet crudes.',
    sulfurLimitPct: 1.3,
  },
  {
    id: 'crude-shock',
    name: 'Heavy Crude Price Discount',
    description: 'High sulfur heavy grades discounted by 25%. Tests optimizer ability to exploit sour margins.',
    crudePriceMultiplier: 0.75,
  },
  {
    id: 'diesel-surge',
    name: 'Monsoon Diesel Demand Surge',
    description: 'Agricultural & freight demand boosts diesel price by +30% and minimum demand by +25%.',
    dieselPriceBoost: 1.3,
  },
];

export interface RefineryModelResult {
  model: Model;
  crudes: CrudeInfo[];
  products: string[];
  periods: number;
  cduCapacities: number[];
  varIndices: {
    crude: Map<string, number>; // key: `${c}_${t}` -> colIdx
    sales: Map<string, number>; // key: `${p}_${t}` -> colIdx
    inv: Map<string, number>;   // key: `${p}_${t}` -> colIdx
  };
  rowIndices: {
    cdu: number[];             // period -> rowIdx
    sulfur: number[];          // period -> rowIdx
    balance: Map<string, number>; // `${p}_${t}` -> rowIdx
  };
}

export function buildRefineryModel(scenarioId = 'baseline'): RefineryModelResult {
  const scenario = REFINERY_SCENARIOS.find(s => s.id === scenarioId) ?? REFINERY_SCENARIOS[0];

  const crudes: CrudeInfo[] = refinerySeed.crudes.map(c => ({
    ...c,
    price: scenario.crudePriceMultiplier ? c.price * scenario.crudePriceMultiplier : c.price,
  }));

  const products: string[] = refinerySeed.products;
  const periods: number = refinerySeed.periods;
  const cduCapacities: number[] = refinerySeed.cdu_capacity_kbd.map(cap =>
    scenario.cduCapacityMultiplier ? cap * scenario.cduCapacityMultiplier : cap
  );
  const sulfurLimit: number = scenario.sulfurLimitPct ?? refinerySeed.sulfur_limit_pct;

  const productPrices: Record<string, number> = { ...refinerySeed.product_price_per_bbl };
  if (scenario.dieselPriceBoost) {
    productPrices['Diesel'] *= scenario.dieselPriceBoost;
  }

  const builder = new ModelBuilder();
  builder.name = `REFINERY_${scenario.id.toUpperCase()}`;
  builder.sense = 'max';

  const varCrude = new Map<string, number>();
  const varSales = new Map<string, number>();
  const varInv = new Map<string, number>();

  // 1. Columns (Variables)
  // For each period t:
  //   - x_{c, t} for each crude c: 0 <= x <= avail_kbd, cost = -price_c (since we maximize revenue - cost)
  //   - s_{p, t} for each product p: demandMin <= s <= demandMax, price = +price_p
  //   - inv_{p, t} for each product p: 0 <= inv <= tankLimit, cost = -0.50 (holding cost $/bbl/period)
  for (let t = 0; t < periods; t++) {
    // Crudes
    for (const c of crudes) {
      const colIdx = builder.addCol(`${c.name.replace(/\s+/g, '_')}_T${t}`);
      builder.setColBound(colIdx, 'UP', c.avail_kbd);
      builder.setColBound(colIdx, 'LO', 0);
      builder.setObjCoeff(colIdx, -c.price);
      varCrude.set(`${c.name}_${t}`, colIdx);
    }

    // Product Sales
    for (const p of products) {
      const minDemand = (refinerySeed.product_demand_min_kbd as Record<string, number>)[p] ?? 0;
      const maxDemand = (refinerySeed.product_demand_max_kbd as Record<string, number>)[p] ?? 100;
      const price = productPrices[p] ?? 50;

      const colIdx = builder.addCol(`SALE_${p}_T${t}`);
      builder.setColBound(colIdx, 'LO', minDemand);
      builder.setColBound(colIdx, 'UP', maxDemand);
      builder.setObjCoeff(colIdx, price);
      varSales.set(`${p}_${t}`, colIdx);
    }

    // Product Inventories
    for (const p of products) {
      const tankLimit = (refinerySeed.tank_limit_kbd as Record<string, number>)[p] ?? 100;
      const colIdx = builder.addCol(`INV_${p}_T${t}`);
      builder.setColBound(colIdx, 'LO', 0);
      builder.setColBound(colIdx, 'UP', tankLimit);
      builder.setObjCoeff(colIdx, -0.50); // inventory carrying cost
      varInv.set(`${p}_${t}`, colIdx);
    }
  }

  // 2. Constraints
  const rowCDU: number[] = [];
  const rowSulfur: number[] = [];
  const rowBalance = new Map<string, number>();

  for (let t = 0; t < periods; t++) {
    // A. CDU Capacity: sum_c x_{c, t} <= cduCapacity_t
    const cduRow = builder.addRow(`CDU_CAP_T${t}`, 'L');
    builder.setRhs(cduRow, cduCapacities[t], 'L');
    for (const c of crudes) {
      const cCol = varCrude.get(`${c.name}_${t}`)!;
      builder.setEntry(cduRow, cCol, 1.0);
    }
    rowCDU.push(cduRow);

    // B. Sulfur Limit: sum_c (sulfur_c - sulfurLimit) * x_{c, t} <= 0
    const sulfRow = builder.addRow(`SULFUR_SPEC_T${t}`, 'L');
    builder.setRhs(sulfRow, 0.0, 'L');
    for (const c of crudes) {
      const cCol = varCrude.get(`${c.name}_${t}`)!;
      builder.setEntry(sulfRow, cCol, c.sulfur_pct - sulfurLimit);
    }
    rowSulfur.push(sulfRow);

    // C. Material Balance: sum_c (yield_{c, p} * x_{c, t}) + inv_{p, t-1} - inv_{p, t} - s_{p, t} = 0
    for (let pIdx = 0; pIdx < products.length; pIdx++) {
      const p = products[pIdx];
      const balRow = builder.addRow(`BAL_${p}_T${t}`, 'E');
      rowBalance.set(`${p}_${t}`, balRow);

      let rhs = 0;
      if (t === 0) {
        // Initial inventory is fixed
        const initInv = (refinerySeed.initial_inventory_kbd as Record<string, number>)[p] ?? 0;
        rhs = -initInv; // shifted to RHS: ... = -initInv
      } else {
        // inv_{p, t-1}
        const prevInvCol = varInv.get(`${p}_${t - 1}`)!;
        builder.setEntry(balRow, prevInvCol, 1.0);
      }
      builder.setRhs(balRow, rhs, 'E');

      // Crudes yield
      for (const c of crudes) {
        const cCol = varCrude.get(`${c.name}_${t}`)!;
        const y = c.yields[pIdx] ?? 0;
        builder.setEntry(balRow, cCol, y);
      }

      // - inv_{p, t}
      const curInvCol = varInv.get(`${p}_${t}`)!;
      builder.setEntry(balRow, curInvCol, -1.0);

      // - s_{p, t}
      const curSalesCol = varSales.get(`${p}_${t}`)!;
      builder.setEntry(balRow, curSalesCol, -1.0);
    }
  }

  const model = builder.build();

  return {
    model,
    crudes,
    products,
    periods,
    cduCapacities,
    varIndices: { crude: varCrude, sales: varSales, inv: varInv },
    rowIndices: { cdu: rowCDU, sulfur: rowSulfur, balance: rowBalance },
  };
}
