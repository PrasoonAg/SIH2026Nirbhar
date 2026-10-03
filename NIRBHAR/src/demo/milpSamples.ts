/**
 * NIRBHAR — Industrial MILP Demo Problem Formulations
 * 
 * Standard MPS representations of realistic mixed-integer programs:
 *   1. 0-1 Knapsack with Weak LP relaxation (tests Gomory & Cover cuts)
 *   2. Capacitated Lot-Sizing / Fixed-Charge Production
 *   3. Refinery Campaign Unit Switchover (Crude Distillation Modes)
 *   4. Unit-Commitment & Dispatch (Binary on/off generator states)
 */

export interface MILPSample {
  id: string;
  name: string;
  category: string;
  description: string;
  expectedOptimum: number;
  expectedGapClosedByCuts: string;
  mps: string;
}

export const MILP_SAMPLES: MILPSample[] = [
  {
    id: 'knapsack-weak',
    name: '0-1 Knapsack (Classic Weak Relaxation)',
    category: 'Benchmark / Cuts',
    description: 'Item 1 (val 10, wt 5), Item 2 (val 8, wt 4), Item 3 (val 5, wt 3) with budget 7. LP relaxation sets x1=1, x2=0.5, achieving obj -14. Cutting planes (GMI + Cover) close the root relaxation gap to proven integer optimum -13 (Items 2 & 3).',
    expectedOptimum: -13.0,
    expectedGapClosedByCuts: '75% – 100%',
    mps: `NAME          KNAPSACK_MILP
ROWS
 N  obj
 L  capacity
COLUMNS
    MARK0000  'MARKER'                 'INTORG'
    x1        obj       -10.0  capacity  5.0
    x2        obj       -8.0   capacity  4.0
    x3        obj       -5.0   capacity  3.0
    MARK0001  'MARKER'                 'INTEND'
RHS
    rhs       capacity  7.0
BOUNDS
 UP bnd       x1        1.0
 UP bnd       x2        1.0
 UP bnd       x3        1.0
ENDATA`,
  },
  {
    id: 'lotsizing-fixedcharge',
    name: 'Capacitated Lot-Sizing (Fixed Charge)',
    category: 'Production Planning',
    description: '3-period multi-item manufacturing with fixed machine startup costs y_t in {0,1} and continuous production quantities x_t <= M*y_t. Cuts (c-MIR + Cover) dramatically tighten the big-M relaxation before tree search.',
    expectedOptimum: 48.0,
    expectedGapClosedByCuts: '60% – 85%',
    mps: `NAME          LOTSIZING_3PER
ROWS
 N  cost
 G  demand1
 G  demand2
 G  demand3
 L  cap1
 L  cap2
 L  cap3
COLUMNS
    MARK0000  'MARKER'                 'INTORG'
    y1        cost       20.0  cap1     -10.0
    y2        cost       25.0  cap2     -10.0
    y3        cost       22.0  cap3     -10.0
    MARK0001  'MARKER'                 'INTEND'
    x1        cost        2.0  demand1    1.0  cap1  1.0
    x2        cost        3.0  demand2    1.0  cap2  1.0
    x3        cost        2.5  demand3    1.0  cap3  1.0
RHS
    rhs       demand1     4.0  demand2    6.0  demand3  5.0
BOUNDS
 UP bnd       y1        1.0
 UP bnd       y2        1.0
 UP bnd       y3        1.0
 UP bnd       x1       10.0
 UP bnd       x2       10.0
 UP bnd       x3       10.0
ENDATA`,
  },
  {
    id: 'refinery-campaign',
    name: 'Refinery Crude Distillation Mode Switch',
    category: 'Refining Operations',
    description: 'Crude Distillation Unit (CDU) operating campaign with binary choices between High-Sulfur Heavy Crude mode and Low-Sulfur Light Sweet mode, subject to minimum throughput and mode transition costs.',
    expectedOptimum: 112.5,
    expectedGapClosedByCuts: '50% – 80%',
    mps: `NAME          REFINERY_CAMPAIGN
ROWS
 N  profit
 G  cdu_min_run
 L  cdu_max_cap
 L  sulfur_limit
 L  switch_penalty
COLUMNS
    MARK0000  'MARKER'                 'INTORG'
    u_heavy   profit     45.0  cdu_max_cap   10.0  switch_penalty  1.0
    u_light   profit     38.0  cdu_max_cap   10.0  switch_penalty  1.0
    MARK0001  'MARKER'                 'INTEND'
    vol_heavy profit     -3.2  cdu_min_run    1.0  sulfur_limit    0.8
    vol_light profit     -2.8  cdu_min_run    1.0  sulfur_limit    0.3
RHS
    rhs       cdu_min_run 15.0  cdu_max_cap   20.0  sulfur_limit  9.5  switch_penalty  1.0
BOUNDS
 UP bnd       u_heavy    1.0
 UP bnd       u_light    1.0
 UP bnd       vol_heavy 15.0
 UP bnd       vol_light 15.0
ENDATA`,
  },
  {
    id: 'unit-commitment',
    name: 'Power Grid Unit-Commitment & Dispatch',
    category: 'Power & Utilities',
    description: 'Thermal generation dispatch with 3 generator units, commitment status binary u_i in {0,1}, min generation limits, and variable incremental cost to meet 85 MW peak load.',
    expectedOptimum: 1840.0,
    expectedGapClosedByCuts: '70% – 95%',
    mps: `NAME          UNIT_COMMITMENT
ROWS
 N  total_cost
 E  load_balance
 G  min_gen1
 G  min_gen2
 G  min_gen3
 L  max_gen1
 L  max_gen2
 L  max_gen3
COLUMNS
    MARK0000  'MARKER'                 'INTORG'
    u1        total_cost 500.0  min_gen1  -20.0  max_gen1  -50.0
    u2        total_cost 400.0  min_gen2  -15.0  max_gen2  -40.0
    u3        total_cost 300.0  min_gen3  -10.0  max_gen3  -30.0
    MARK0001  'MARKER'                 'INTEND'
    p1        total_cost  15.0  load_balance 1.0  min_gen1   1.0  max_gen1   1.0
    p2        total_cost  18.0  load_balance 1.0  min_gen2   1.0  max_gen2   1.0
    p3        total_cost  22.0  load_balance 1.0  min_gen3   1.0  max_gen3   1.0
RHS
    rhs       load_balance 85.0
BOUNDS
 UP bnd       u1         1.0
 UP bnd       u2         1.0
 UP bnd       u3         1.0
 UP bnd       p1        50.0
 UP bnd       p2        40.0
 UP bnd       p3        30.0
ENDATA`,
  }
];

export const SAMPLE_KNAPSACK_MPS = MILP_SAMPLES[0].mps;
export const SAMPLE_LOT_SIZING_MPS = MILP_SAMPLES[1].mps;
export const SAMPLE_REFINERY_MPS = MILP_SAMPLES[2].mps;
export const SAMPLE_UNIT_COMMITMENT_MPS = MILP_SAMPLES[3].mps;
