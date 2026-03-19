# Coastal Table — Dummy Dataset Documentation

**Restaurant:** Coastal Table (fictional mid-to-upscale West Coast restaurant)
**Location:** Vancouver, BC
**Period:** February 1–28, 2026 (28 days)
**POS System:** Square for Restaurants Plus
**Seats:** 72 (8× 2-tops, 10× 4-tops, 2× 6-tops, 4 bar seats)

---

## Summary Statistics

| Metric | Value |
|---|---|
| POS Transactions | 2,853 payments + 15 refunds |
| Line Items Sold | 19,323 |
| Gross Sales (POS) | $453,594 |
| Net Sales (POS) | $450,182 |
| Total Tips | $68,574 |
| Total Labor Cost | $68,409 |
| Labor % of Net Sales | 15.2% |
| Delivery Orders | 474 (Uber Eats + DoorDash) |
| Delivery Gross Revenue | $33,490 |
| Delivery Net Payout | $23,223 |
| Reservations | 1,119 |
| No-Show Rate | 8.1% |
| Active Customers | 150 |
| Timecard Records | 416 |

---

## File Inventory

### 01_transactions.csv — Payment-Level Sales Data

**Grain:** One row per payment transaction.
**Schema source:** Square Transactions CSV export (Section 5A of discovery doc).
**Join key:** `Transaction_ID` links to `02_item_details.csv`.

| Column | Type | Description |
|---|---|---|
| `Date` | datetime | Payment timestamp (PST) |
| `Transaction_ID` | string | Unique payment ID — **join key** to item details |
| `Payment_ID` | string | Payment reference (same as Txn ID; would differ for split payments) |
| `Event_Type` | string | "Payment" or "Refund" |
| `Location` | string | Always "Main Dining" (single-location) |
| `Source` | string | "Square POS" or "Square Online" |
| `Customer_Name` | string | Linked customer name (blank if anonymous) |
| `Customer_ID` | string | Customer directory ID (blank if anonymous) |
| `Device_Name` | string | POS terminal that processed payment |
| `Team_Member` | string | Server/staff who rang it up |
| `Gross_Sales` | decimal | Total before discounts |
| `Discounts` | decimal | Discount amount (negative when applied) |
| `Net_Sales` | decimal | Gross minus discounts |
| `Tax` | decimal | GST (5%) + PST (7%) on prepared food |
| `Tip` | decimal | Credit/debit card tip |
| `Total_Collected` | decimal | Net + Tax + Tip |
| `Fees` | decimal | Square processing fees (negative) |
| `Net_Total` | decimal | Total Collected minus Fees |
| `Payment_Method` | string | Visa, Mastercard, Interac Debit, Cash, Amex, Gift Card |
| `Card_Entry_Method` | string | Tap, Chip, or blank |
| `Card_Last_4` | string | Last 4 digits of card |
| `Cash_Rounding` | decimal | Canadian penny rounding |
| `Order_Type` | string | Dine-In, Takeout, or Delivery |

**Assumptions:**
- ~45% of transactions have a linked customer (loyalty/card-on-file)
- Order type mix: ~72% dine-in, ~14% takeout, ~14% delivery
- Payment mix: ~41% Visa, ~26% Mastercard, ~16% Interac Debit, ~10% Cash, ~4% Amex, ~3% Gift Card
- Tip rates: Dine-in 15-25% (mode 20%), takeout 0-15%, delivery $0 (driver tip)
- 15 refund transactions scattered across the month

---

### 02_item_details.csv — Line-Item Sales Data

**Grain:** One row per menu item per transaction.
**Schema source:** Square Item Details CSV export (Section 5B of discovery doc).
**Join key:** `Transaction_ID` links to `01_transactions.csv`.

| Column | Type | Description |
|---|---|---|
| `Date` | datetime | Same as parent transaction |
| `Transaction_ID` | string | **Join key** to transactions file |
| `Event_Type` | string | "Payment" |
| `Location` | string | "Main Dining" |
| `Team_Member` | string | Server |
| `Item_Name` | string | Menu item name |
| `Item_Variation` | string | Always "Regular" (no size variations in this dataset) |
| `Category` | string | Appetizers, Mains, Brunch, Desserts, Drinks - Wine/Cocktails/Beer/Non-Alc |
| `Reporting_Category` | string | Food Factor reporting taxonomy (Food - Starters, Food - Entrees, etc.) |
| `SKU` | string | Item SKU code |
| `GTIN` | string | Blank (not used in restaurants) |
| `Quantity` | integer | Always 1 per row |
| `Unit_Price` | decimal | Base menu price |
| `Gross_Sales` | decimal | Price + modifier upcharge |
| `Discounts` | decimal | Item-level discount (negative) |
| `Net_Sales` | decimal | Gross minus discounts |
| `Tax` | decimal | BC tax on this item |
| `Modifiers` | string | Modifier name and price (e.g., "Extra Prawns (+$4.00)") |
| `Modifier_Amount` | decimal | Total modifier upcharge |
| `Notes` | string | Item notes (blank in this dataset) |
| `Cost` | decimal | COGS/food cost for this item |

**Menu composition:** 44 items across 10 categories. West Coast / Pacific Northwest cuisine. Brunch items appear only on Sundays. Average food cost ratio ~33%.

---

### 03_timecards.csv — Labor / Shift Data

**Grain:** One row per shift per team member.
**Schema source:** Square Timecards CSV export (Section 5C of discovery doc).

| Column | Type | Description |
|---|---|---|
| `Team_Member` | string | Staff name |
| `Team_Member_ID` | string | Unique staff ID |
| `Job_Title` | string | Server, Host, Bartender, Busser, Head Chef, Line Cook, Prep Cook, Dishwasher |
| `Location` | string | "Main Dining" |
| `Date` | date | Shift date |
| `Clock_In` | datetime | Clock-in time |
| `Clock_Out` | datetime | Clock-out time |
| `Total_Hours` | decimal | Total elapsed hours |
| `Paid_Hours` | decimal | Excluding unpaid breaks |
| `Regular_Hours` | decimal | Up to 8 hours |
| `Overtime_Hours` | decimal | Beyond 8 hours at 1.5× rate |
| `Hourly_Rate` | decimal | BC wages ($17.40 minimum, up to $32 for Head Chef) |
| `Labor_Cost` | decimal | Regular × rate + OT × rate × 1.5 |
| `Break_Start` | datetime | Break start (blank if no break) |
| `Break_End` | datetime | Break end |
| `Break_Paid` | string | "No" for unpaid breaks |
| `Declared_Cash_Tips` | decimal | Cash tips declared at clock-out (FOH only) |
| `Pooled_Tips_By_Transaction` | decimal | Auto-allocated pooled tips |
| `Timecard_Notes` | string | Shift notes |

**Staff roster:** 21 total (12 FOH + 9 BOH). Staffing levels scale with day-of-week: full staff Fri-Sat, reduced Mon-Wed. Head Chef works every day except Monday.

**Wage assumptions:**
- BC minimum wage: $17.40/hr (servers, hosts, bussers, dishwashers)
- Bartenders: $19.00-19.50/hr
- Senior servers: $18.00-18.50/hr
- Line cooks: $20.00-22.00/hr
- Prep cooks: $18.00-18.50/hr
- Head Chef: $32.00/hr

---

### 04_delivery_orders.csv — Delivery Platform Financial Data

**Grain:** One row per delivery order (normalized across platforms).
**Schema source:** Unified Delivery Export schema (Section 9A of delivery discovery doc).

| Column | Type | Description |
|---|---|---|
| `Platform` | string | "Uber Eats" or "DoorDash" |
| `Order_ID` | string | Platform-prefixed order ID (UE-XXXXXXXX or DD-XXXXXXXX) |
| `Order_Date` | datetime | Order timestamp |
| `Order_Status` | string | Completed or Canceled |
| `Dining_Mode` | string | Always "Delivery" |
| `Gross_Sales` | decimal | Food subtotal before fees/commission |
| `Tax` | decimal | GST + PST |
| `GST` | decimal | Federal 5% |
| `PST` | decimal | Provincial 7% |
| `Tip` | decimal | Customer tip (goes to driver, not restaurant) |
| `Commission_Amount` | decimal | Platform commission (negative) |
| `Commission_Rate` | decimal | 0.30 (UE) or 0.25 (DD) |
| `Marketing_Fee` | decimal | Platform marketing charges |
| `Promo_Cost_Restaurant` | decimal | Restaurant-funded promo portion |
| `Promo_Cost_Platform` | decimal | Platform-funded promo portion (positive) |
| `Service_Fee` | decimal | Other platform fees |
| `Adjustments` | decimal | Error refunds, chargebacks |
| `Net_Payout` | decimal | Amount deposited to restaurant |
| `Payout_Date` | date | Deposit date (3-7 days after order) |
| `Item_Count` | integer | Items in order |
| `Customer_Type` | string | New or Returning |
| `Prep_Time_Minutes` | decimal | Kitchen prep time |
| `Delivery_Time_Minutes` | decimal | Door-to-door delivery time |
| `Customer_Rating` | decimal | 3.0-5.0 scale (blank if not rated) |
| `POS_Transaction_ID` | string | Blank (would link to POS if integrated) |

**Assumptions:**
- Delivery menu is a subset of 12 items with ~15% price markup over dine-in
- Uber Eats commission: 30%, DoorDash: 25%
- ~4% cancellation rate
- Daily volume: 8-28 orders depending on day (UE dominates ~60/40)
- Tips go to drivers, not the restaurant

---

### 05_reservations.csv — Reservation Data (OpenTable-Style)

**Grain:** One row per reservation.

| Column | Type | Description |
|---|---|---|
| `Reservation_ID` | string | Sequential ID (RES-000001) |
| `Date` | date | Reservation date |
| `Reservation_Time` | datetime | Booked time slot |
| `Party_Size` | integer | 1-6 guests |
| `Service` | string | Lunch, Dinner, or Brunch (Sunday) |
| `Source` | string | OpenTable, Resy, Phone, Walk-In, Website |
| `Status` | string | Completed, No-Show, Canceled, Late Cancel |
| `Booked_At` | datetime | When reservation was made |
| `Lead_Time_Days` | integer | Days between booking and dining |
| `Guest_Name` | string | Guest name |
| `Guest_Email` | string | Guest email |
| `Guest_Phone` | string | Guest phone (604 area code) |
| `Guest_Notes` | string | Host/staff notes about guest |
| `Special_Request` | string | Guest's special requests |
| `Table_ID` | string | Assigned table (e.g., 4-TOP-03) |
| `Seated_Time` | datetime | Actual seated time (blank if no-show/canceled) |
| `Departed_Time` | datetime | Table cleared time |
| `Turn_Time_Minutes` | integer | Seat-to-clear duration |
| `Wait_Time_Minutes` | integer | Wait after reservation time |
| `Server_Assigned` | string | Server who handled the table |

**Assumptions:**
- Source mix: 40% OpenTable, 25% Resy, 15% Phone, 15% Walk-In, 5% Website
- No-show rate: ~8% (industry average for upscale casual)
- Cancellation rate: ~8%, Late cancellation: ~6%
- Turn times: 55-85 min lunch, 75-120 min dinner (+10-25 for parties of 5+)
- Lead times: ~50% same-day bookings (trending with industry data)
- Party size distribution weighted toward 2-tops (mode)

---

### 06_customer_directory.csv — Customer Profiles

**Grain:** One row per known customer.
**Schema source:** Square Customer Directory export (Section 5E of discovery doc).

| Column | Type | Description |
|---|---|---|
| `Customer_ID` | string | Unique customer identifier |
| `First_Name` | string | First name |
| `Last_Name` | string | Last name |
| `Email` | string | Email address |
| `Phone` | string | Phone (604 area code) |
| `Created_Date` | date | First seen in system |
| `Total_Visits` | integer | Visit count in February |
| `Total_Spend` | decimal | Total spend in February |
| `Last_Visit` | date | Most recent visit |
| `Loyalty_Points` | integer | Accumulated loyalty points |
| `Groups` | string | Customer segments (Regular, VIP, Weekend Regular, etc.) |
| `Notes` | string | Staff notes |

**Note:** Only 150 of 300 possible customers visited during February. Customer linkage rate is ~45% of transactions (rest are anonymous/cash).

---

## Data Relationships

```
01_transactions.csv ──(Transaction_ID)──> 02_item_details.csv
01_transactions.csv ──(Customer_ID)─────> 06_customer_directory.csv
05_reservations.csv ──(Guest matching)──> 06_customer_directory.csv (name/email join)
04_delivery_orders.csv ──(POS_Transaction_ID)──> 01_transactions.csv (if POS-integrated)
03_timecards.csv ──(Team_Member)────────> 01_transactions.csv (server matching)
05_reservations.csv ──(Server_Assigned)─> 03_timecards.csv (labor-to-covers join)
```

## Day-of-Week Volume Patterns

| Day | Lunch Txns | Dinner Txns | Delivery | Reservations |
|---|---|---|---|---|
| Monday | ~25 | ~45 | ~10 | ~20 |
| Tuesday | ~28 | ~50 | ~12 | ~25 |
| Wednesday | ~30 | ~55 | ~13 | ~28 |
| Thursday | ~38 | ~70 | ~16 | ~45 |
| Friday | ~42 | ~85 | ~22 | ~55 |
| Saturday | ~45 | ~95 | ~24 | ~60 |
| Sunday | ~55 (brunch) | ~65 | ~18 | ~45 |

*All values are approximate baselines with ±15% daily variance applied.*

---

## Known Limitations & Intentional Gaps

1. **No inventory/COGS tracking file** — Consistent with the reality that most restaurants don't have structured inventory exports. COGS is embedded at the item level in `02_item_details.csv` via the `Cost` column.
2. **Delivery `POS_Transaction_ID` is blank** — Simulates a restaurant where delivery platforms are NOT integrated with the POS (common scenario). Cross-referencing requires timestamp/amount matching.
3. **Reservation-to-POS linkage is implicit** — No direct join key between reservations and transactions. Matching requires fuzzy joins on date, time, party size, and server — exactly as it works in real life.
4. **Customer data is sparse** — Only ~45% of transactions have linked customers. This is realistic for restaurants without aggressive loyalty programs.
5. **Brunch items only appear on Sundays** — Menu availability changes by day, which is common for restaurants with weekend brunch service.
6. **No review/sentiment data** — Review data is handled by Food Factor's separate MCP-powered review analysis agent, not generated here.

---

*Generated by Food Factor data pipeline. Seed: 42 (reproducible).*
