# Coastal Table — TouchBistro Dummy Dataset Documentation

**Restaurant:** Coastal Table (fictional mid-to-upscale West Coast restaurant)
**Location:** Vancouver, BC
**Period:** March 1–30, 2026 (30 days)
**POS System:** TouchBistro (iPad POS, base plan + Reservations add-on)
**Seats:** 72 (8× 2-tops, 10× 4-tops, 2× 6-tops, 4 bar seats)
**Sections:** Main Dining (20 tables), Patio (8 tables), Bar (4 seats)

---

## Summary Statistics

| Metric | Value |
|---|---|
| POS Bills | 2,932 + 7 refunds |
| Line Items Sold | 18,209 (49 voids) |
| Gross Sales (POS) | $427,284 |
| Net Sales (POS) | $423,257 |
| Total Tax Collected | $32,359 |
| Total Tips | $78,123 |
| Total Labor Cost | $67,341 |
| Labor % of Net Sales | 15.9% |
| Delivery Orders | 466 completed + 20 canceled |
| Delivery Gross Revenue | $37,985 |
| Delivery Net Payout | $26,696 |
| Reservations | 1,195 |
| No-Show Rate | 8.4% |
| Shift Records | 520 |

---

## File Inventory

### TouchBistro_01_detailed_sales.csv — Master Sales Export

**Source report:** iPad: Admin → Reports → Accounting → Detailed Sales CSV
**Grain:** One row per line item per bill (the richest single export in TouchBistro).
**Rows:** 18,265

| Column | Data Type | Example | Notes |
|---|---|---|---|
| `Bill_Number` | integer | 1001 | Unique bill identifier. Primary key for bill-level analysis |
| `Order_Number` | integer | 1001 | Usually matches Bill_Number; would differ in split-bill scenarios |
| `Date` | date | 2026-03-01 | Date the bill was closed |
| `Time` | time | 19:23:47 | Time the bill was closed |
| `Waiter` | string | Sarah M. | Staff member who served the table |
| `Section` | string | Main Dining | Floor plan section: Main Dining, Patio, Bar, Cash Register |
| `Table` | string | 12 | Table number (blank for takeout/delivery) |
| `Seats` | integer | 4 | Number of guests on the bill |
| `Order_Type` | string | Dine-In | Dine-In, Takeout, or Bar Tab |
| `Menu_Item` | string | Seafood Linguine | Item ordered |
| `Menu_Category` | string | Mains | Category: Appetizers, Mains, Desserts, Wine, Cocktails, Beer, Non-Alcoholic, Brunch |
| `Sales_Category` | string | Food | Higher-level: Food, Alcohol, Non-Alcoholic |
| `Quantity` | integer | 1 | Quantity ordered (negative for returns) |
| `Price` | decimal | 28.00 | Menu price per unit |
| `Gross_Sales` | decimal | 32.00 | Price + modifier upcharges |
| `Discount_Name` | string | Happy Hour 20% | Discount name (blank if none) |
| `Discount_Amount` | decimal | -6.40 | Discount dollar amount (negative) |
| `Net_Sales` | decimal | 25.60 | Gross minus discount |
| `Modifiers` | string | Extra Prawns (+$4.00) | Modifier text with price |
| `Modifier_Amount` | decimal | 4.00 | Total modifier upcharge |
| `Tax_1_Name` | string | GST | Federal goods & services tax |
| `Tax_1_Amount` | decimal | 1.28 | GST at 5% on net sales |
| `Tax_2_Name` | string | PST | Provincial sales tax |
| `Tax_2_Amount` | decimal | 0.00 | PST at 10% on alcohol only; $0 on food in BC |
| `Total_Tax` | decimal | 1.28 | GST + PST |
| `Tip` | decimal | 0.00 | Tip allocated to last item row on each bill (TouchBistro convention) |
| `Auto_Gratuity` | decimal | 0.00 | Auto-grat for parties of 6+ (18%) |
| `Payment_Method` | string | Visa | Visa, Mastercard, Interac Debit, Cash, Amex, Gift Card |
| `Is_Void` | string | No | "Yes" if item was voided after being sent to kitchen |
| `Is_Return` | string | No | "Yes" if this is a refund line |
| `Notes` | string | | Item-level notes |

**Key differences from Square:** This single file replaces Square's two-file model (Transactions CSV + Item Details CSV). Bill-level data (payment method, tip, section) and item-level data (menu item, price, modifiers) coexist in every row. Tip appears only on the last item row per bill.

---

### TouchBistro_02_sales_item_totals.csv — Menu Engineering Export

**Source report:** iPad: Admin → Reports → Menu → Sales Item Totals
**Grain:** One row per menu item (aggregated over the full 30-day period).
**Rows:** 49

| Column | Data Type | Example | Notes |
|---|---|---|---|
| `Menu_Item` | string | Seafood Linguine | Item name |
| `Menu_Category` | string | Mains | Category |
| `Sales_Category` | string | Food | Higher-level category |
| `Quantity_Sold` | integer | 502 | Times ordered in period |
| `Gross_Sales` | decimal | 14,243.00 | Total revenue before discounts |
| `Returns` | integer | 0 | Return count |
| `Return_Amount` | decimal | 0.00 | Dollar value of returns |
| `Voids` | integer | 0 | Items voided (sent to kitchen, then canceled) |
| `Net_Sales` | decimal | 14,018.55 | Gross minus returns/discounts |
| `Item_Cost` | decimal | 8.40 | Per-unit food cost |
| `Total_Cost` | decimal | 4,216.80 | Quantity × Item Cost |
| `Food_Cost_Pct` | string | 30.1% | Total Cost / Net Sales |

**Use case:** Menu engineering (stars/plowhorses/puzzles/dogs matrix), food cost analysis, pricing optimization.

---

### TouchBistro_03_detailed_shift_report.csv — Labor Export

**Source report:** iPad: Admin → Reports → Labor → Detailed Shift Report
**Grain:** One row per clock-in event per staff member.
**Rows:** 520

| Column | Data Type | Example | Notes |
|---|---|---|---|
| `Staff_Member` | string | Sarah M. | Employee name |
| `Staff_Type` | string | FOH | Front-of-house or BOH (back-of-house) |
| `Job_Title` | string | Server | Role: Server, Host, Bartender, Busser, Head Chef, Line Cook, Prep Cook, Dishwasher |
| `Date` | date | 2026-03-01 | Shift date |
| `Clock_In` | datetime | 2026-03-01 16:00:00 | Clock-in time |
| `Clock_Out` | datetime | 2026-03-01 23:30:00 | Clock-out time |
| `Hours_Worked` | string | 7:00 | Hours and minutes worked (HH:MM format, after deducting unpaid break) |
| `Hourly_Rate` | decimal | 18.50 | Rate of pay |
| `Pay` | decimal | 129.50 | Calculated pay (regular + OT at 1.5×) |
| `Cash_Tips` | decimal | 35.00 | Cash tips declared at clock-out (FOH only) |
| `Credit_Card_Tips` | decimal | 42.50 | CC tips attributed to this staff member |
| `Break_Start` | datetime | 2026-03-01 19:30:00 | Break start (blank if shift < 5 hours) |
| `Break_End` | datetime | 2026-03-01 20:00:00 | Break end |

**Staff roster:** 21 total (12 FOH + 9 BOH)

| Role | Count | Hourly Rate |
|---|---|---|
| Server | 6 | $17.40–$18.50 |
| Host | 2 | $17.40 |
| Bartender | 2 | $19.00–$19.50 |
| Busser | 2 | $17.40 |
| Head Chef | 1 | $32.00 |
| Line Cook | 4 | $20.00–$22.00 |
| Prep Cook | 2 | $18.00–$18.50 |
| Dishwasher | 2 | $17.40 |

**Staffing pattern:** Full staff Fri-Sat, reduced Mon-Wed. Head Chef off Mondays (~60% chance). Overtime (~5% of shifts) occurs when shifts exceed 8 hours, paid at 1.5× rate per BC Employment Standards.

---

### TouchBistro_04_delivery_orders.csv — Delivery Platform Financial Data

**Source:** Normalized export from Uber Eats Merchant Portal + DoorDash Merchant Portal
**Grain:** One row per delivery order.
**Rows:** 486

| Column | Data Type | Example | Notes |
|---|---|---|---|
| `Platform` | string | Uber Eats | Uber Eats or DoorDash |
| `Order_ID` | string | UE-71193393 | Platform-prefixed order ID |
| `Order_Date` | datetime | 2026-03-01 11:44:57 | Order timestamp |
| `Order_Status` | string | Completed | Completed or Canceled |
| `Dining_Mode` | string | Delivery | Always "Delivery" |
| `Gross_Sales` | decimal | 64.40 | Food subtotal (15% markup over dine-in) |
| `Tax` | decimal | 3.22 | GST only (food = no PST in BC) |
| `GST` | decimal | 3.22 | Federal 5% |
| `PST` | decimal | 0.00 | Provincial (0% on food) |
| `Tip` | decimal | 6.06 | Customer tip (goes to driver, not restaurant) |
| `Commission_Amount` | decimal | -19.32 | Platform commission (negative) |
| `Commission_Rate` | decimal | 0.30 | UE: 30%, DD: 25% |
| `Marketing_Fee` | decimal | 0.00 | Platform marketing charges |
| `Promo_Cost_Restaurant` | decimal | 0.00 | Restaurant-funded promo portion |
| `Promo_Cost_Platform` | decimal | 0.00 | Platform-funded promo (positive offset) |
| `Service_Fee` | decimal | -0.84 | Other platform fees |
| `Adjustments` | decimal | 0.00 | Error refunds, chargebacks |
| `Net_Payout` | decimal | 44.24 | Amount deposited to restaurant |
| `Payout_Date` | date | 2026-03-08 | Deposit date (3-7 days after order) |
| `Item_Count` | integer | 2 | Items in order |
| `Customer_Type` | string | Returning | New or Returning |
| `Prep_Time_Minutes` | decimal | 17.5 | Kitchen prep time |
| `Delivery_Time_Minutes` | decimal | 22.0 | Door-to-door delivery time |
| `Customer_Rating` | decimal | 5.0 | 3.0-5.0 scale (blank if not rated) |
| `POS_Transaction_ID` | string | | Blank (not POS-integrated — requires timestamp matching) |

**Platform split:** ~60% Uber Eats, ~40% DoorDash. Delivery menu is a subset of 12 food items with 15% price markup. ~4% cancellation rate.

**Critical note:** Delivery commission/fees are NOT captured in the TouchBistro POS. These orders appear in the POS as regular sales (via Deliverect/UrbanPiper middleware) but the commission deductions happen externally. This file is the reconciliation source.

---

### TouchBistro_05_reservations.csv — Reservation Data

**Source:** TouchBistro Reservations add-on (or OpenTable/Resy if external)
**Grain:** One row per reservation.
**Rows:** 1,195

| Column | Data Type | Example | Notes |
|---|---|---|---|
| `Reservation_ID` | string | RES-000001 | Sequential ID |
| `Date` | date | 2026-03-01 | Reservation date |
| `Reservation_Time` | datetime | 2026-03-01 18:30:00 | Booked time slot |
| `Party_Size` | integer | 4 | 1-6 guests |
| `Service` | string | Dinner | Lunch, Dinner, or Brunch (Sunday) |
| `Source` | string | OpenTable | OpenTable (40%), Resy (25%), Phone (15%), Walk-In (15%), Website (5%) |
| `Status` | string | Completed | Completed, No-Show, Canceled, Late Cancel |
| `Booked_At` | datetime | 2026-02-28 14:30:00 | When reservation was made |
| `Lead_Time_Days` | integer | 1 | Days between booking and dining |
| `Guest_Name` | string | Rachel Kim | Guest name |
| `Guest_Email` | string | rachel.kim@gmail.com | Guest email (blank ~30%) |
| `Guest_Phone` | string | 604-934-7704 | Guest phone (blank ~15%) |
| `Guest_Notes` | string | VIP guest | Host/staff notes |
| `Special_Request` | string | Window seat preferred | Guest's special requests |
| `Table_ID` | string | 4-TOP-03 | Assigned table |
| `Seated_Time` | datetime | 2026-03-01 18:35:00 | Actual seated time (blank if no-show/canceled) |
| `Departed_Time` | datetime | 2026-03-01 20:15:00 | Table cleared time |
| `Turn_Time_Minutes` | integer | 100 | Seat-to-clear duration |
| `Wait_Time_Minutes` | integer | 5 | Wait after reservation time |
| `Server_Assigned` | string | Sarah M. | Server who handled the table |

**Status rates:** ~78% Completed, ~8% No-Show, ~8% Canceled, ~6% Late Cancel. Turn times: 55-85 min (lunch/brunch), 75-120 min (dinner), +10-25 min for parties of 5+. ~50% same-day bookings.

---

### TouchBistro_06_payments_refund_totals.csv — Payment Method Summary

**Source report:** iPad: Admin → Reports → Payments → Payments and Refund Totals
**Grain:** One row per payment method (aggregated over full period).
**Rows:** 6

| Column | Data Type | Example | Notes |
|---|---|---|---|
| `Payment_Method` | string | Visa | Payment type |
| `Total_Amount` | decimal | 207,030.62 | Total collected (inclusive of tax + tip) |
| `Tips` | decimal | 30,378.45 | Tips on this payment method |
| `Refunds` | decimal | 68.25 | Refunds issued via this method |
| `Transaction_Count` | integer | 1,161 | Number of transactions |

**Payment mix:** Visa ~40%, Mastercard ~27%, Interac Debit ~17%, Cash ~10%, Amex ~3%, Gift Card ~3%.

---

## Data Relationships

```
TouchBistro_01_detailed_sales.csv
  ├── Bill_Number ──> aggregates to bill-level (join on Bill_Number for bill totals)
  ├── Waiter ──────> TouchBistro_03_detailed_shift_report.csv (Staff_Member match)
  ├── Menu_Item ───> TouchBistro_02_sales_item_totals.csv (aggregated view)
  └── Payment_Method > TouchBistro_06_payments_refund_totals.csv (aggregated view)

TouchBistro_05_reservations.csv
  ├── Server_Assigned ──> TouchBistro_03_detailed_shift_report.csv (Staff_Member)
  └── Date + Time + Party_Size ──> fuzzy join to sales bills (no direct key)

TouchBistro_04_delivery_orders.csv
  └── POS_Transaction_ID (blank) ──> would link to sales if POS-integrated
```

**Key difference from Square:** TouchBistro's Detailed Sales CSV is a single denormalized file containing both bill-level and item-level data. There is no separate Transactions CSV — bill attributes (payment method, tip, section, waiter) repeat on every item row. Aggregation requires `GROUP BY Bill_Number` for bill-level metrics.

---

## Day-of-Week Volume Patterns

| Day | Lunch/Brunch Bills | Dinner Bills | Delivery | Reservations |
|---|---|---|---|---|
| Monday | ~22 | ~42 | ~10 | ~21 |
| Tuesday | ~25 | ~48 | ~12 | ~26 |
| Wednesday | ~28 | ~52 | ~13 | ~29 |
| Thursday | ~35 | ~68 | ~16 | ~46 |
| Friday | ~40 | ~82 | ~22 | ~56 |
| Saturday | ~42 | ~90 | ~24 | ~62 |
| Sunday | ~50 (brunch) | ~62 | ~18 | ~46 |

*All values are approximate baselines with ±15% daily variance applied.*

---

## BC Tax Assumptions

- **GST (5%):** Applied to all food, alcohol, and non-alcoholic items
- **PST (10%):** Applied to alcohol only. Food and non-alcoholic beverages are PST-exempt in BC
- Sales reports show **pre-tax, post-discount** figures (Net_Sales column)
- Payment reports show **tax-inclusive** totals (TouchBistro convention)
- This means Sales totals ≠ Payment totals unless tax is accounted for

---

## Known Limitations & Intentional Design Choices

1. **No Customer Directory export.** TouchBistro does not offer a single-file customer export like Square. Customer data lives in the CRM/Loyalty add-ons. Guest names in reservations are the closest proxy.

2. **Delivery POS_Transaction_ID is blank.** Simulates a restaurant where delivery platforms are routed through middleware (Deliverect/UrbanPiper) but not fully POS-integrated. Cross-referencing requires timestamp/amount matching — exactly how it works in practice.

3. **Reservation-to-POS linkage is implicit.** No direct join key between reservations and sales bills. Matching requires fuzzy joins on date, time, party size, and server — realistic for all POS systems.

4. **Modifier data is concatenated text.** Modifiers appear as a single text string (e.g., "Extra Prawns (+$4.00)") in the Modifiers column, with the total upcharge in Modifier_Amount. This matches TouchBistro's real export behavior — parsing requires string manipulation.

5. **Tips appear on last item row only.** TouchBistro allocates tip and auto-gratuity to the last line item per bill. To get bill-level tips, aggregate by Bill_Number and sum.

6. **Brunch items only appear on Sundays.** Menu availability changes by day, consistent with the restaurant's weekend brunch service.

7. **No Cost of Goods Sold Report.** COGS data is embedded in the Sales Item Totals file (Item_Cost, Total_Cost, Food_Cost_Pct columns). A separate COGS Report would be redundant with this dataset.

8. **No Inventory/Ingredient data.** Consistent with reality — most restaurants don't have structured ingredient-level tracking. TouchBistro supports it but requires manual recipe setup that few restaurants complete.

9. **30-day period (not 28).** This dataset covers March 1–30, 2026 (30 days) vs. the Square dataset's February 1–28, 2026 (28 days). Slightly larger dataset by design to provide a full calendar month minus one day.

---

## Comparison to Square Dummy Dataset

| Dimension | Square Dataset | TouchBistro Dataset |
|---|---|---|
| Period | Feb 1–28, 2026 (28 days) | Mar 1–30, 2026 (30 days) |
| Sales file structure | 2 files (Transactions + Item Details, joined on Transaction_ID) | 1 file (Detailed Sales CSV — denormalized) |
| Bill identifier | Transaction_ID (UUID-style) | Bill_Number (sequential integer) |
| Tax handling | Single Tax column | Split: GST + PST columns |
| Customer data | Customer Directory CSV (150 profiles) | No equivalent (CRM add-on required) |
| Payment summary | Derivable from transactions | Dedicated Payments & Refund Totals export |
| Menu engineering | Derivable from item details | Dedicated Sales Item Totals export |
| Staff type field | Job_Title only | Staff_Type (FOH/BOH) + Job_Title |

---

*Generated by Food Factor data pipeline. Seed: 42 (reproducible).*
