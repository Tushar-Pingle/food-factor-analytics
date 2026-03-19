# POS Pipeline Output Standardization Report

## Executive Summary

This report documents a comprehensive audit of three POS system pipelines (Square, TouchBistro, and Lightspeed) to identify output inconsistencies, missing features, and opportunities for standardization. The analysis reveals significant divergence in:

- **Output format**: JSON exports vs. in-memory DataFrames only
- **Chart completeness**: 23 charts (Square) vs. 2 charts (TouchBistro) vs. 20 charts (Lightspeed)
- **KPI field naming and availability**: 11 fields in Square's executive summary vs. 15 distributed across Lightspeed
- **Analysis coverage**: All 6+ analyzer categories implemented in Square, only 3 in TouchBistro (with labor stubbed), all 6 in Lightspeed
- **Delivery and Reservation analysis**: Fully implemented in Square and Lightspeed; loaded but unanalyzed in TouchBistro

**Key Finding**: No two pipelines produce identical output artifacts or field names, creating significant integration challenges for downstream consumption.

---

## 1. Output Files Comparison

| Aspect | Square | TouchBistro | Lightspeed |
|--------|--------|------------|------------|
| **Primary Export Format** | Single `report_data.json` | None (dicts/DataFrames in memory) | None (charts only) |
| **Secondary Exports** | N/A | Implied DataFrames | N/A |
| **Structured Data Export** | JSON | None | None |
| **CSV Export** | None listed | None | None |
| **Chart Directory** | Unspecified | Current directory | `output/charts/` |
| **Chart Count** | 23 | 2 of 14 planned | 20 |
| **KPI Summary Format** | `executive_summary` dict in JSON | Inline in function returns | `labor_summary` + `revenue_summary` dicts |

---

## 2. Chart Generation Comparison

### Implementation Status

| Chart Purpose | Square | TouchBistro | Lightspeed | Filename Standardization |
|---|---|---|---|---|
| **Daily Revenue Trend** | ✅ `sales_daily_trend.png` | ✅ `01_daily_revenue.png` | ✅ Included in scorecard | CONFLICT: 3 different names |
| **Day of Week Revenue** | ✅ `sales_dow_revenue.png` | ✅ `02_day_of_week.png` | ✅ Included in scorecard | CONFLICT: 3 different names |
| **Daypart Analysis** | ✅ `sales_daypart.png` | ❌ Not implemented | ✅ Included in scorecard | Lightspeed + Square only |
| **Order Type Split** | ✅ `sales_order_type.png` | ❌ Not implemented | ✅ Included in scorecard | Lightspeed + Square only |
| **Revenue Heatmap** | ✅ `sales_heatmap.png` | ❌ Not implemented | ✅ Included in scorecard | Lightspeed + Square only |
| **Sales by Category** | ✅ `sales_category.png` | ✅ `Sales_Category` data exists | ✅ Included in scorecard | Data exists but chart gaps in TB |
| **Average Check Size** | ✅ `sales_avg_check.png` | ✅ `avg_check` KPI | ✅ Included in scorecard | All track but chart missing in TB |
| **Menu Engineering Matrix** | ✅ `menu_engineering_matrix.png` | ❌ Not implemented | ❌ Not implemented | Square only |
| **Menu Food Cost** | ✅ `menu_food_cost.png` | ❌ Not implemented | ❌ Not implemented | Square only |
| **Menu Top Performers** | ✅ `menu_top_{suffix}.png` | ❌ Not implemented | ❌ Not implemented | Square only |
| **Payment Methods** | ✅ `payment_methods.png` | ❌ Not implemented | ❌ Not implemented | Square only |
| **Labor vs Sales** | ✅ `labor_vs_sales.png` | ❌ Stubbed (TODO) | ✅ Included in scorecard | TouchBistro gap |
| **Labor by Role** | ✅ `labor_by_role.png` | ❌ Stubbed (TODO) | ✅ Included in scorecard | TouchBistro gap |
| **Sales Per Labor Hour** | ✅ `labor_splh.png` | ❌ Stubbed (TODO) | ✅ Included in scorecard | TouchBistro gap |
| **Labor FOH vs BOH** | ✅ `labor_foh_boh.png` | ❌ Stubbed (TODO) | ✅ Included in scorecard | TouchBistro gap |
| **Delivery Platform Compare** | ✅ `delivery_platform_compare.png` | ❌ Not implemented | ✅ Included in scorecard | TouchBistro gap |
| **Delivery Daily Trend** | ✅ `delivery_daily_trend.png` | ❌ Not implemented | ✅ Included in scorecard | TouchBistro gap |
| **Delivery Waterfall** | ✅ `delivery_waterfall.png` | ❌ Not implemented | ✅ Included in scorecard | TouchBistro gap |
| **Reservation Source Mix** | ✅ `res_source_mix.png` | ❌ Not implemented | ✅ Included in scorecard | TouchBistro gap |
| **Reservation No-Show DOW** | ✅ `res_noshow_dow.png` | ❌ Not implemented | ✅ Included in scorecard | TouchBistro gap |
| **Reservation DOW Pattern** | ✅ `res_dow_pattern.png` | ❌ Not implemented | ✅ Included in scorecard | TouchBistro gap |
| **Operations KPI Scorecard** | ❌ Not explicitly listed | ❌ Not implemented | ✅ `00_kpi_scorecard.png` | Lightspeed unique |
| **Server Performance** | ❌ Labor role exists | ✅ `server_performance` data exists | ✅ `employee_performance` | All track differently |
| **Operational Flags** | ✅ `ops_server_performance.png` | ✅ Auto-gratuity + comp analysis | ✅ Void anomalies analysis | Different implementations |

---

## 3. KPI Fields Comparison

### Fields Present in All Three Pipelines

| KPI Field | Square | TouchBistro | Lightspeed | Definition |
|-----------|--------|------------|-----------|-----------|
| `total_revenue` or equivalent | `net_sales` | `total_net` | `total_net_revenue` | Revenue after discounts |
| `total_transactions` or equivalent | `total_transactions` | `total_bills` | `transaction_count` | Count of orders/bills/transactions |
| `total_covers` | `total_covers` | `total_covers` | `total_covers` | Guest count |
| `avg_check_size` or equivalent | `avg_check_size` | `avg_check` | `avg_check` | Revenue per transaction |
| `labor_pct` or equivalent | `labor_pct` | ❌ Not tracked | `labor_pct` | Labor as % of revenue |
| `tips` or equivalent | ❌ Not in KPI summary | `total_tips` | `total_tips` | Total tips collected |

### Square Executive Summary KPI Fields (11 total)

```json
{
  "net_sales": float,
  "avg_daily_revenue": float,
  "avg_check_size": float,
  "total_transactions": int,
  "labor_pct": float,
  "splh": float,
  "delivery_margin": float,
  "noshow_rate": float,
  "total_covers": int,
  "menu_stars": int,
  "menu_dogs": int
}
```

### TouchBistro KPI Fields (15 total, distributed across return values)

```
total_gross, total_net, total_bills, total_covers, avg_check,
revenue_per_cover, total_discounts, discount_rate_pct, total_tips,
avg_tip_pct, items_sold, avg_items_per_bill, operating_days,
avg_daily_revenue, avg_daily_covers
```

**Note**: No centralized summary object; fields scattered across function returns.

### Lightspeed KPI Fields (14 total, split across labor_summary + revenue_summary)

**labor_summary:**
```
total_labor_cost, total_paid_hours, labor_pct, splh, total_shifts,
num_employees, overtime_hours, overtime_premium, avg_hourly_rate
```

**revenue_summary:**
```
total_net_revenue, total_with_tax, total_tips, transaction_count,
num_operating_days, avg_daily_revenue, avg_check, total_covers,
avg_daily_covers, rev_per_cover, avg_tip_rate
```

---

## 4. Extended Fields (Unique to One System)

### Square-Only Fields

| Field | Location | Purpose |
|-------|----------|---------|
| `menu_stars` | `executive_summary` | Top performers in menu engineering |
| `menu_dogs` | `executive_summary` | Low performers in menu engineering |
| `delivery_margin` | `executive_summary` | Delivery profitability |
| `noshow_rate` | `executive_summary` | Reservation no-show percentage |
| `customer_directory` | `report_data.json` | Customer contact data (Square-specific) |
| `cross_domain_insights` | Analyzer outputs | Multi-domain pattern analysis |

### TouchBistro-Only Fields

| Field | Purpose |
|-------|---------|
| `total_gross` | Revenue before discounts |
| `discount_rate_pct` | Discount percentage |
| `revenue_per_cover` | Revenue normalized by covers |
| `items_sold` | Menu item quantity metric |
| `avg_items_per_bill` | Items per transaction |
| `operating_days` | Number of operational days in period |
| `avg_daily_covers` | Covers per operating day |
| `section_performance` | Floor area/section breakdown |
| `Sales_Category` split | Food vs Alcohol differentiation |
| `server_performance` | Per-server metrics |
| `comp_analysis` | Complimentary item tracking |
| `auto_gratuity_tracking` | Auto-gratuity application patterns |

### Lightspeed-Only Fields

| Field | Purpose |
|-------|---------|
| `total_with_tax` | Revenue including tax |
| `num_operating_days` | Operating day count |
| `num_employees` | Employee count |
| `overtime_hours` | Hours beyond standard shift |
| `overtime_premium` | Overtime cost premium |
| `avg_hourly_rate` | Average employee hourly cost |
| `total_shifts` | Shift count |
| `avg_daily_covers` | Covers per day |
| `rev_per_cover` | Revenue per guest |
| `avg_tip_rate` | Tip percentage |
| `floor_performance` | By-section/table revenue |
| `register_breakdown` | By-register metrics |
| `cash_handling` | Cash reconciliation analysis |
| `employee_performance` | Rev/hour, tips/hour per employee |
| `RevPASH` | Revenue per available shift hour |
| `tip_anomalies` | Unusual tip patterns |
| `late_night_voids` | Voids during late hours |
| `high_value_voids` | High-dollar voided transactions |

---

## 5. Analyzer Coverage Gaps

| Analyzer | Square | TouchBistro | Lightspeed | Notes |
|----------|--------|------------|-----------|-------|
| **SalesAnalyzer** ✅ | ✅ Full | ✅ `run_sales_analysis` | ✅ `run_revenue_analysis` | All three present (TB/LS naming differs) |
| **PaymentAnalyzer** ✅ | ✅ Full | ✅ `run_payment_analysis` | ✅ `run_payment_analysis` | All three present |
| **DeliveryAnalyzer** | ✅ Full | ❌ Data loaded, not analyzed | ✅ `run_delivery_analysis` | **TouchBistro gap** |
| **ReservationAnalyzer** | ✅ Full | ❌ Data loaded, not analyzed | ✅ `run_reservation_analysis` | **TouchBistro gap** |
| **LaborAnalyzer** | ✅ Full | ❌ Stubbed (TODO only) | ✅ `run_labor_analysis` | **TouchBistro gap** |
| **OperationalFlagAnalyzer** | ✅ Full | ✅ `run_operational_flags` | ✅ `run_operational_flags` | All three present |

---

## 6. Data Structure Differences

### Square
- **Output**: Single `report_data.json` file containing all data
- **Structure**: Nested dict with sections for each analyzer
- **Executive Summary**: Centralized KPI summary object
- **Data Class**: Uses `SquareDataset` dataclass for type safety
- **Export Mechanism**: `ReportExporter` class handles JSON serialization

### TouchBistro
- **Output**: No file export; returns dicts and DataFrames in memory
- **Structure**: Function returns (no centralized summary)
- **Executive Summary**: None; KPIs embedded in return values
- **Data Class**: No structured dataclass
- **Export Mechanism**: Caller responsible for persistence
- **Gap**: This breaks pipeline portability

### Lightspeed
- **Output**: Charts saved to `output/charts/`; no structured data file
- **Structure**: No JSON export; summary dicts created but not persisted
- **Executive Summary**: Two separate summary dicts (`labor_summary`, `revenue_summary`)
- **Data Class**: No structured dataclass
- **Export Mechanism**: Charts only; data exists in memory but not exported
- **Gap**: Loses structured data after analysis; difficult to integrate

---

## 7. Chart Naming Convention Analysis

### Naming Patterns by System

**Square**: Hierarchical prefix + descriptive name
- Pattern: `{domain}_{description}.png`
- Examples: `sales_daily_trend.png`, `labor_vs_sales.png`, `res_source_mix.png`
- Strengths: Immediately identifiable domain
- Weakness: No sequence/ordering

**TouchBistro**: Sequential numbering with description (partial implementation)
- Pattern: `{XX}_{description}.png`
- Examples: `01_daily_revenue.png`, `02_day_of_week.png`
- Strengths: Enforced ordering
- Weakness: Only 2 of 14 implemented; numbering scheme incomplete

**Lightspeed**: Sequential numbering with domain-specific naming
- Pattern: `{XX}_{description}.png`
- Examples: `00_kpi_scorecard.png` through `19_void_by_server.png`
- Strengths: Sequential ordering, complete implementation
- Weakness: Less hierarchical clarity than Square

### Chart Filename Conflicts (Same Chart, Different Names)

| Chart Type | Square | TouchBistro | Lightspeed |
|-----------|--------|------------|-----------|
| Daily Revenue | `sales_daily_trend.png` | `01_daily_revenue.png` | Embedded in scorecard |
| Day of Week | `sales_dow_revenue.png` | `02_day_of_week.png` | Embedded in scorecard |
| Server/Staff Performance | `ops_server_performance.png` | `server_performance` (no chart) | `employee_performance` data + embedded |

---

## 8. Data Loading vs. Analysis Gaps

| Data Type | Square | TouchBistro | Lightspeed |
|-----------|--------|------------|-----------|
| Sales Data | ✅ Analyzed | ✅ Analyzed | ✅ Analyzed |
| Payment Data | ✅ Analyzed | ✅ Analyzed | ✅ Analyzed |
| Delivery Data | ✅ Full analyzer | ❌ **Loaded but NOT analyzed** | ✅ Full analyzer |
| Reservation Data | ✅ Full analyzer | ❌ **Loaded but NOT analyzed** | ✅ Full analyzer |
| Labor Data | ✅ Full analyzer | ❌ **Stubbed with TODO** | ✅ Full analyzer |

**Critical Finding**: TouchBistro loads delivery and reservation data but does not perform any analysis. Labor analyzer is stubbed with only TODO comments.

---

## 9. Recommended Standard Output Contract

To enable interoperability and support downstream integration, all three pipelines should conform to the following standard:

### 9.1 Output File Format

**Requirement**: All pipelines MUST export a single `report_data.json` file containing:

```json
{
  "metadata": {
    "pipeline": "square|touchbistro|lightspeed",
    "start_date": "YYYY-MM-DD",
    "end_date": "YYYY-MM-DD",
    "generated_at": "ISO-8601-timestamp",
    "period_days": int,
    "operating_days": int
  },
  "executive_summary": {
    "net_sales": float,
    "gross_sales": float,
    "total_discounts": float,
    "total_tips": float,
    "total_transactions": int,
    "total_covers": int,
    "avg_check": float,
    "avg_daily_revenue": float,
    "avg_daily_covers": float,
    "revenue_per_cover": float,
    "operating_days": int
  },
  "labor_summary": {
    "total_labor_cost": float,
    "total_paid_hours": float,
    "labor_pct": float,
    "splh": float,
    "total_shifts": int,
    "num_employees": int,
    "overtime_hours": float,
    "overtime_premium": float,
    "avg_hourly_rate": float
  },
  "sales_analysis": { ... },
  "payment_analysis": { ... },
  "delivery_analysis": { ... },
  "reservation_analysis": { ... },
  "labor_analysis": { ... },
  "operational_flags": { ... },
  "charts_generated": [
    "00_kpi_scorecard.png",
    "01_daily_revenue.png",
    ...
  ]
}
```

### 9.2 Chart Naming Standard

**Requirement**: All charts MUST use sequential numbering with domain prefix:

```
{XX}_{domain}_{description}.png
```

**Chart Manifest** (20 required charts):

| # | Domain | Chart Name | Purpose |
|---|--------|-----------|---------|
| 00 | ops | `00_ops_kpi_scorecard.png` | Executive KPI dashboard |
| 01 | sales | `01_sales_daily_revenue.png` | Daily revenue trend |
| 02 | sales | `02_sales_dow_revenue.png` | Revenue by day of week |
| 03 | sales | `03_sales_daypart.png` | Revenue by daypart |
| 04 | sales | `04_sales_order_type.png` | Revenue by order type |
| 05 | sales | `05_sales_category.png` | Revenue by menu category |
| 06 | sales | `06_sales_heatmap.png` | Revenue heatmap (hour × day) |
| 07 | sales | `07_sales_avg_check.png` | Average check trend |
| 08 | menu | `08_menu_engineering_matrix.png` | Menu engineering matrix |
| 09 | menu | `09_menu_top_performers.png` | Top menu items |
| 10 | menu | `10_menu_low_performers.png` | Low performers (dogs) |
| 11 | payment | `11_payment_methods.png` | Payment method breakdown |
| 12 | labor | `12_labor_vs_sales.png` | Labor cost vs sales |
| 13 | labor | `13_labor_by_role.png` | Labor cost by role |
| 14 | labor | `14_labor_splh.png` | Sales per labor hour trend |
| 15 | labor | `15_labor_foh_boh.png` | FOH vs BOH labor split |
| 16 | delivery | `16_delivery_platform_compare.png` | Delivery platform comparison |
| 17 | delivery | `17_delivery_daily_trend.png` | Delivery revenue trend |
| 18 | delivery | `18_delivery_waterfall.png` | Delivery cost waterfall |
| 19 | reservation | `19_res_source_mix.png` | Reservation source breakdown |
| 20 | reservation | `20_res_noshow_pattern.png` | No-show by day of week |

### 9.3 Analyzer Implementation Requirements

**Requirement**: All pipelines MUST implement all six analyzers:

1. ✅ `SalesAnalyzer` — revenue, category, daypart, order type
2. ✅ `PaymentAnalyzer` — payment methods, discounts, tips
3. ✅ `DeliveryAnalyzer` — delivery platform performance, margins
4. ✅ `ReservationAnalyzer` — no-show rates, source mix, patterns
5. ✅ `LaborAnalyzer` — cost, SPLH, FOH/BOH split, roles
6. ✅ `OperationalFlagAnalyzer` — anomalies, high-value voids, late-night patterns

### 9.4 Executive Summary KPI Fields (Mandatory)

**Requirement**: `executive_summary` object MUST contain these 13 fields:

| Field | Type | Definition |
|-------|------|-----------|
| `net_sales` | float | Revenue after discounts |
| `gross_sales` | float | Total revenue before discounts |
| `total_discounts` | float | Sum of all discounts |
| `total_tips` | float | Sum of all tips |
| `total_transactions` | int | Count of orders/bills |
| `total_covers` | int | Total guest count |
| `avg_check` | float | Net sales / transactions |
| `avg_daily_revenue` | float | Net sales / operating_days |
| `avg_daily_covers` | float | Total covers / operating_days |
| `revenue_per_cover` | float | Net sales / total covers |
| `operating_days` | int | Days with transactions |
| `labor_pct` | float | Labor cost / net sales |
| `splh` | float | Net sales / total paid hours |

### 9.5 Labor Summary KPI Fields (Mandatory)

**Requirement**: `labor_summary` object MUST contain these 9 fields:

| Field | Type | Definition |
|-------|------|-----------|
| `total_labor_cost` | float | Sum of all wages + benefits |
| `total_paid_hours` | float | Sum of all hours paid |
| `labor_pct` | float | Labor cost / net sales |
| `splh` | float | Net sales / total paid hours |
| `total_shifts` | int | Count of shifts worked |
| `num_employees` | int | Unique employee count |
| `overtime_hours` | float | Hours beyond standard |
| `overtime_premium` | float | Overtime cost premium |
| `avg_hourly_rate` | float | Total labor cost / total hours |

### 9.6 Analysis Section Structure

Each analyzer output MUST follow this structure in `report_data.json`:

```json
"{analyzer_name}_analysis": {
  "summary": {
    "key_metric_1": value,
    "key_metric_2": value
  },
  "trends": [
    { "date": "YYYY-MM-DD", "metric": value },
    ...
  ],
  "breakdown": {
    "category_1": value,
    "category_2": value
  },
  "insights": [
    { "finding": "description", "impact": "high|medium|low" }
  ]
}
```

---

## 10. Migration Path

### Phase 1: Standardize Square (Reference Implementation)
- **Status**: Already exceeds standard
- **Action**: Verify all 20 charts are generated; rename any non-conforming charts
- **Chart additions needed**: Verify `00_ops_kpi_scorecard.png` is generated

### Phase 2: Enhance TouchBistro
- **Priority 1**: Implement file export to `report_data.json`
- **Priority 2**: Complete delivery and reservation analyzers (data loaded but unanalyzed)
- **Priority 3**: Complete labor analyzer (currently stubbed)
- **Priority 4**: Generate all 20 charts
- **Priority 5**: Standardize KPI field names per contract

### Phase 3: Enhance Lightspeed
- **Priority 1**: Implement structured `report_data.json` export
- **Priority 2**: Rename charts to conform to `{XX}_{domain}_{description}.png` pattern
- **Priority 3**: Consolidate labor and revenue summaries into single standardized structure

### Phase 4: Validation & Integration
- **Requirement**: All pipelines produce identical field names for same concept
- **Requirement**: All pipelines generate all 20 charts
- **Requirement**: All pipelines export `report_data.json` with identical schema

---

## 11. Summary of Gaps

### Critical (Blocks Interoperability)

| Gap | Severity | System(s) | Impact |
|-----|----------|-----------|--------|
| No JSON export | **CRITICAL** | TouchBistro, Lightspeed | Downstream consumers cannot access structured data |
| Labor analyzer stubbed | **CRITICAL** | TouchBistro | Labor analysis completely unavailable |
| Delivery analyzer not run | **CRITICAL** | TouchBistro | Delivery data loaded but not analyzed |
| Reservation analyzer not run | **CRITICAL** | TouchBistro | Reservation data loaded but not analyzed |
| Chart naming inconsistency | **HIGH** | All three | Consumers must hardcode system-specific filenames |
| KPI field name inconsistency | **HIGH** | All three | Field mapping required for each system |

### Medium (Affects Completeness)

| Gap | System(s) |
|-----|-----------|
| 12 of 14 charts not implemented | TouchBistro |
| Inconsistent summary structure | TouchBistro/Lightspeed (split across objects) |
| Menu engineering analysis gaps | TouchBistro, Lightspeed |

### Low (Enhancement Opportunities)

| Gap | System(s) |
|-----|-----------|
| Auto-gratuity tracking not in others | TouchBistro only |
| RevPASH calculation not universal | Lightspeed only |
| Detailed cash handling analysis | Lightspeed only |

---

## 12. Recommendations

1. **Immediate**: Adopt the standardized output contract for all new development
2. **Short-term** (1-2 sprints): Migrate TouchBistro to comply with standard (highest priority)
3. **Short-term** (1-2 sprints): Add JSON export to Lightspeed
4. **Medium-term** (2-4 sprints): Rename all Lightspeed charts to standard format
5. **Long-term**: Create shared analyzer base classes to reduce code duplication
6. **Documentation**: Maintain this contract specification in version control

---

**Document Generated**: 2026-03-18
**Audit Status**: Complete
**Standardization Coverage**: 0% (baseline for future tracking)
