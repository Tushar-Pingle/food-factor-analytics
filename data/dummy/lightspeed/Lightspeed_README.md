# Ember & Oak — Lightspeed Restaurant Dummy Dataset Documentation

**Restaurant:** Ember & Oak (fictional mid-to-upscale Pacific Northwest + Japanese-influenced restaurant)
**Location:** Vancouver, BC
**Period:** March 1–30, 2026 (30 days)
**POS System:** Lightspeed Restaurant K-Series (with L-Series export format for compatibility)
**Seats:** ~82 (10× 4-tops, 4× 2-tops, 4× 6-tops in Main Dining; 4× 4-tops + 2× 2-tops on Patio; 4× 2-tops at Bar)

---

## Summary Statistics

| Metric | Value |
|---|---|
| POS Receipts | 2,825 (45 voided) |
| Line Items Sold | 21,755 |
| Modifier Applications | 1,898 |
| Payments | 2,780 |
| Net Sales (POS) | $486,140 |
| Tips (POS) | $86,389 |
| Total Labor Cost | $63,543 |
| Labor % of Net Sales | 13.1% |
| Delivery Orders | 504 (Uber Eats + DoorDash) |
| Delivery Gross Revenue | $34,375 |
| Delivery Net Payout | $27,417 |
| Reservations | 1,361 |
| No-Show Rate | 7.9% |
| Active Customers (linked) | 159 |
| Shift Records | 503 |
| Menu Items | 43 |

---

## File Inventory

### Lightspeed_01_receipts.csv — Receipt-Level Data

**Grain:** One row per receipt/transaction.
**Schema source:** Lightspeed L-Series Receipts Export (Section 5A of discovery doc).
**Join key:** `Receipt_ID` links to `Lightspeed_02_receipt_items.csv`, `Lightspeed_03_modifiers.csv`, and `Lightspeed_04_payments.csv`.

| Column | Type | Description |
|---|---|---|
| `Receipt_ID` | string | Unique receipt identifier (format: R000001.01) — **primary join key** |
| `Sequence_Number` | integer | Sequential receipt number |
| `Creation_Date` | datetime | When the receipt was first created |
| `Finalized_Date` | datetime | When the receipt was paid/closed |
| `Status` | string | "Paid" or "Voided" |
| `Type` | string | "Dine-In" or "Takeout" |
| `Void_Status` | string | Blank (normal) or "Voided" |
| `Table_ID` | string | Table identifier (T-01 through T-24) |
| `Table_Name` | string | Display name (Table 1, Patio 3, Bar 2, etc.) |
| `Floor_ID` | string | Floor plan ID (F-001, F-002, F-003) |
| `Floor_Name` | string | "Main Dining", "Patio", or "Bar" |
| `Course_Number` | string | Blank at receipt level (populated at item level) |
| `User_ID` | string | Server/staff member ID |
| `Username` | string | Server name |
| `Customer_ID` | string | Linked customer ID (blank if anonymous, ~45% linked) |
| `Customer_Name` | string | Customer name |
| `Customer_Email` | string | Customer email |
| `Number_of_Seats` | integer | Cover count (party size) |
| `Net_Total` | decimal | Subtotal of all items before tax |
| `Taxes` | string | Tax summary (e.g., "GST: $4.50") |
| `Total` | decimal | Net + tax |
| `Tip` | decimal | Tip on receipt |
| `Extra` | string | Additional notes |
| `Parent_ID` | string | Original receipt if split (blank in this dataset) |
| `Has_Children` | boolean | Whether receipt was split (always False here) |
| `Delivery_Date` | datetime | Delivery timestamp (blank for dine-in/takeout) |

**Assumptions:**
- ~45% of receipts have a linked customer
- Order type mix: ~88% dine-in, ~12% takeout (delivery handled separately)
- ~2% void rate
- Tip rates: Dine-in 15-25% (mode 20%), Takeout 0-15%

---

### Lightspeed_02_receipt_items.csv — Line-Item Sales Data

**Grain:** One row per menu item per receipt.
**Schema source:** Lightspeed L-Series Receipt Items Export (Section 5B of discovery doc).
**Join key:** `Receipt_ID` links to `Lightspeed_01_receipts.csv`.

| Column | Type | Description |
|---|---|---|
| `Receipt_ID` | string | **Join key** to receipts file |
| `Creation_Date` | datetime | When item was added to the order |
| `Created_By` | string | Staff member who added the item |
| `Product_ID` | string | Unique product ID (P-1001 through P-8005) |
| `Item_Name` | string | Menu item display name |
| `Kitchen_Name` | string | Kitchen display abbreviation |
| `Status` | string | "Sent" (to kitchen) |
| `Tax_Exclusive_Price` | decimal | Price before tax (includes modifiers, minus discounts) |
| `Tax_Inclusive_Price` | decimal | Price including tax |
| `Amount` | integer | Quantity ordered (always 1 per row) |
| `Tax_Percentage` | decimal | Tax rate: 5.0% (food/non-alc) or 15.0% (alcohol) |
| `Tax_Amount` | decimal | Tax charged on this item |
| `Total_Price` | decimal | Tax-inclusive total |
| `Total_Tax_Excl_Price` | decimal | Tax-exclusive total |
| `Category` | string | Appetizers, Mains, Desserts, Cocktails, Wine, Beer, Non-Alcoholic, Brunch |
| `Category_Type` | string | "Food" or "Beverage" |
| `Seat_Number` | integer | Which seat this item belongs to |
| `Course_Number` | integer | 1 (starters/drinks), 2 (mains), 3 (desserts) |
| `PLU` | string | Product lookup unit |
| `Extra` | string | Item-level notes |

**Menu composition:** 43 items across 8 categories. Pacific Northwest + Japanese-influenced cuisine. Brunch items appear only on Sundays. Average food cost ~33%.

---

### Lightspeed_03_modifiers.csv — Structured Modifier Data

**Grain:** One row per modifier application per item.
**Schema source:** Lightspeed L-Series Modifiers Export (Section 5C of discovery doc).
**Join key:** `receipt_id` + `product_id` links to receipt items.

| Column | Type | Description |
|---|---|---|
| `receipt_id` | string | Links to receipt |
| `item_name` | string | Parent item name |
| `product_id` | string | Parent product ID |
| `product_plu` | string | Parent PLU |
| `product_name` | string | Parent product name |
| `mod_id` | string | Unique modifier ID (M-101 through M-108) |
| `mod_plu` | string | Modifier PLU |
| `mod_name` | string | Modifier display name |
| `mod_desc` | string | Modifier description |
| `mod_price_incl` | decimal | Price with tax |
| `mod_price_excl` | decimal | Price without tax |

**Key advantage:** Unlike Square/TouchBistro (concatenated text), Lightspeed provides modifiers as separate structured rows — significantly better for analysis. 8 modifiers defined, ~12% application rate per eligible item.

---

### Lightspeed_04_payments.csv — Payment-Level Data

**Grain:** One row per payment. A receipt can have multiple payments (split tender).
**Schema source:** Lightspeed L-Series Payments Export (Section 5D of discovery doc).
**Join key:** `Receipt_ID` links to receipts.

| Column | Type | Description |
|---|---|---|
| `Receipt_ID` | string | Links to receipt |
| `Payment_ID` | string | Unique payment ID (PAY-000001) |
| `Created_By_Username` | string | Staff who processed payment |
| `Created_Date` | datetime | Payment timestamp |
| `Payment_Name` | string | Visa, Mastercard, Interac Debit, Cash, Amex, Gift Card |
| `Payment_Type` | string | CREDITCARD, DEBITCARD, CASH, GIFTCARD |
| `Payment_Owner_Username` | string | Staff associated with payment |
| `Payment_Status_Name` | string | "Paid" |
| `Amount` | decimal | Total amount paid (includes tip) |
| `Tip` | decimal | Tip amount on this payment |
| `Tip_Owner_Name` | string | Staff who receives the tip |
| `Customer_ID` | string | Customer linked to payment |
| `Customer_Name` | string | Customer name |
| `Cash_Drawer_Name` | string | Main Register or Bar Register |
| `Device_Name` | string | iPad device name |

**Payment mix:** ~38% Visa, ~24% Mastercard, ~18% Interac Debit, ~12% Cash, ~5% Amex, ~3% Gift Card.

---

### Lightspeed_05_labor_shifts.csv — Labor / Shift Data

**Grain:** One row per shift per employee.
**Schema source:** Lightspeed K-Series Labor Report + Staff API Get Shifts (Section 5E of discovery doc).

| Column | Type | Description |
|---|---|---|
| `Shift_ID` | string | Unique shift identifier (SH-00001) |
| `User_ID` | string | Staff member ID |
| `Employee_Name` | string | Staff name |
| `Role` | string | Server, Host, Bartender, Busser, Head Chef, Line Cook, Prep Cook, Dishwasher |
| `User_Group` | string | "FOH" or "BOH" |
| `Location_ID` | string | Business location |
| `Date` | date | Shift date |
| `Clock_In` | datetime | Shift start |
| `Clock_Out` | datetime | Shift end |
| `Total_Hours` | decimal | Total elapsed hours |
| `Paid_Hours` | decimal | Excluding unpaid breaks |
| `Regular_Hours` | decimal | Up to 8 hours |
| `Overtime_Hours` | decimal | Beyond 8 hours at 1.5× rate |
| `Hourly_Rate` | decimal | BC wages |
| `Labor_Cost` | decimal | Regular × rate + OT × rate × 1.5 |
| `Break_Start` | datetime | Break start (blank if no break) |
| `Break_End` | datetime | Break end |
| `Break_Paid` | string | "No" for unpaid breaks |
| `Declared_Cash_Tips` | decimal | Cash tips (FOH only) |
| `Pooled_Tips` | decimal | Auto-allocated pooled tips (FOH only) |
| `Timecard_Notes` | string | Shift notes |

**Staff roster:** 21 total (12 FOH + 9 BOH). Full staff Fri-Sat, reduced Mon-Wed. Head Chef off Mondays.

**Wage assumptions (BC 2026):**
- BC minimum wage: $17.40/hr (hosts, bussers, dishwashers, junior servers)
- Senior servers: $18.00-$18.50/hr
- Bartenders: $19.00-$19.50/hr
- Line cooks: $20.00-$22.00/hr
- Prep cooks: $18.00-$18.50/hr
- Head Chef: $34.00/hr

---

### Lightspeed_06_products.csv — Product Catalog

**Grain:** One row per menu item.
**Schema source:** Lightspeed K-Series Item List Export / L-Series Products CSV (Section 5F of discovery doc).

| Column | Type | Description |
|---|---|---|
| `Product_ID` | string | Unique product ID |
| `Product_Type` | string | "Regular" |
| `Name` | string | Display name |
| `Kitchen_Name` | string | Kitchen abbreviation |
| `PLU` | string | Product lookup unit |
| `Price` | decimal | Dine-in price |
| `Category_ID` | string | Category identifier |
| `Category_Name` | string | Appetizers, Mains, Desserts, Cocktails, Wine, Beer, Non-Alcoholic, Brunch |
| `Tax_Rate` | decimal | 5.0% (food/non-alc) or 15.0% (alcohol: GST + PST) |
| `Takeaway_Tax_Rate` | decimal | 5.0% |
| `Delivery_Tax_Rate` | decimal | 12.0% (GST + PST on delivered prepared food) |
| `Takeaway_Price` | decimal | Same as dine-in |
| `Delivery_Price` | decimal | ~15% markup for delivery menu items (blank if not on delivery menu) |
| `Tax_Exclusive_Price` | decimal | Base price |
| `Cost` | decimal | COGS / food cost |
| `Visible` | boolean | Always True |

**43 items:** 7 appetizers, 10 mains, 4 desserts, 5 cocktails, 5 wines, 3 beers, 4 non-alcoholic, 5 brunch items. Average food cost ratio ~33%.

---

### Lightspeed_07_delivery_orders.csv — Delivery Platform Financial Data

**Grain:** One row per delivery order (normalized across platforms).
**Schema source:** Unified Delivery Export schema (Section 9A of delivery discovery doc).

| Column | Type | Description |
|---|---|---|
| `Platform` | string | "Uber Eats" or "DoorDash" |
| `Order_ID` | string | Platform-prefixed ID (UE-XXXXXXXX or DD-XXXXXXXX) |
| `Order_Date` | datetime | Order timestamp |
| `Order_Status` | string | "Completed" or "Canceled" |
| `Dining_Mode` | string | "Delivery" |
| `Gross_Sales` | decimal | Food subtotal before fees/commission |
| `Tax` | decimal | GST + PST |
| `GST` | decimal | Federal 5% |
| `PST` | decimal | Provincial 7% |
| `Tip` | decimal | Customer tip (goes to driver) |
| `Commission_Amount` | decimal | Platform commission (negative) |
| `Commission_Rate` | decimal | 0.30 (UE) or 0.25 (DD) |
| `Marketing_Fee` | decimal | Platform marketing charges |
| `Promo_Cost_Restaurant` | decimal | Restaurant-funded promo portion |
| `Promo_Cost_Platform` | decimal | Platform-funded promo portion |
| `Service_Fee` | decimal | Other platform fees |
| `Adjustments` | decimal | Error refunds, chargebacks |
| `Net_Payout` | decimal | Amount deposited to restaurant |
| `Payout_Date` | date | Deposit date (3-7 days after order) |
| `Item_Count` | integer | Items in order |
| `Customer_Type` | string | "New" or "Returning" |
| `Prep_Time_Minutes` | decimal | Kitchen prep time |
| `Delivery_Time_Minutes` | decimal | Door-to-door delivery time |
| `Customer_Rating` | decimal | 3.0-5.0 scale (blank if not rated) |
| `POS_Transaction_ID` | string | Blank (delivery not POS-integrated) |

**Assumptions:**
- Platform split: ~58% Uber Eats, ~42% DoorDash
- Commission: Uber Eats 30%, DoorDash 25%
- ~4% cancellation rate
- Delivery menu: subset of items with ~15% price markup
- Tips go to drivers, not the restaurant

---

### Lightspeed_08_reservations.csv — Reservation Data (OpenTable-Style)

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
| `Guest_Phone` | string | Guest phone (604/778/236 area codes) |
| `Guest_Notes` | string | Host/staff notes |
| `Special_Request` | string | Guest requests |
| `Table_ID` | string | Assigned table |
| `Seated_Time` | datetime | Actual seated time (blank if no-show/canceled) |
| `Departed_Time` | datetime | Table cleared time |
| `Turn_Time_Minutes` | integer | Seat-to-clear duration |
| `Wait_Time_Minutes` | integer | Wait after reservation time |
| `Server_Assigned` | string | Server who handled the table |

**Assumptions:**
- Source mix: 40% OpenTable, 25% Resy, 15% Phone, 15% Walk-In, 5% Website
- No-show rate: ~8%, Cancellation: ~8%, Late Cancel: ~6%
- Turn times: 55-85 min lunch, 75-120 min dinner (+10-25 for parties of 5+)
- ~50% same-day/next-day bookings

---

### Lightspeed_09_customer_directory.csv — Customer Profiles

**Grain:** One row per customer who visited during March 2026.

| Column | Type | Description |
|---|---|---|
| `Customer_ID` | string | Unique customer ID |
| `First_Name` | string | First name |
| `Last_Name` | string | Last name |
| `Email` | string | Email address |
| `Phone` | string | Phone number |
| `Created_Date` | date | First seen in system |
| `Total_Visits` | integer | Visit count in March |
| `Total_Spend` | decimal | Total spend in March |
| `Last_Visit` | date | Most recent visit |
| `Loyalty_Points` | integer | Accumulated loyalty points |
| `Groups` | string | Customer segments (General, Regular, VIP, Weekend Regular) |
| `Notes` | string | Staff notes |

---

## Data Relationships

```
Lightspeed_01_receipts.csv ──(Receipt_ID)──> Lightspeed_02_receipt_items.csv
Lightspeed_01_receipts.csv ──(Receipt_ID)──> Lightspeed_03_modifiers.csv
Lightspeed_01_receipts.csv ──(Receipt_ID)──> Lightspeed_04_payments.csv
Lightspeed_01_receipts.csv ──(Customer_ID)─> Lightspeed_09_customer_directory.csv
Lightspeed_08_reservations.csv ──(Guest matching)──> Lightspeed_09_customer_directory.csv (name/email)
Lightspeed_07_delivery_orders.csv ──(POS_Transaction_ID)──> Lightspeed_01_receipts.csv (blank — not integrated)
Lightspeed_05_labor_shifts.csv ──(Employee_Name)──> Lightspeed_01_receipts.csv (server matching)
Lightspeed_08_reservations.csv ──(Server_Assigned)──> Lightspeed_05_labor_shifts.csv (labor-to-covers)
Lightspeed_06_products.csv ──(Product_ID)──> Lightspeed_02_receipt_items.csv (catalog reference)
```

## Day-of-Week Volume Patterns

| Day | Lunch Txns | Dinner Txns | Delivery | Res (Lunch) | Res (Dinner) |
|---|---|---|---|---|---|
| Monday | ~22 | ~40 | ~10 | ~8 | ~14 |
| Tuesday | ~25 | ~48 | ~12 | ~10 | ~18 |
| Wednesday | ~28 | ~52 | ~14 | ~12 | ~22 |
| Thursday | ~35 | ~68 | ~18 | ~18 | ~35 |
| Friday | ~40 | ~82 | ~22 | ~22 | ~45 |
| Saturday | ~42 | ~90 | ~26 | ~24 | ~48 |
| Sunday | ~50 (brunch) | ~60 | ~16 | ~20 | ~30 |

*All values are approximate baselines with ±15% daily variance applied.*

---

## Key Differences from Square & TouchBistro Datasets

| Dimension | Lightspeed (Ember & Oak) | Square (Coastal Table) | TouchBistro |
|---|---|---|---|
| **Receipt model** | Separate Receipts + Receipt Items + Payments + Modifiers (4 files, join on Receipt_ID) | Transactions + Item Details (2 files, join on Transaction_ID) | Combined detailed sales (single file) |
| **Modifier data** | Structured rows in separate CSV — best for analysis | Concatenated text column | Concatenated text |
| **Seat/Course tracking** | ✅ Per-item seat number and course number | ❌ Not available | ❌ Limited |
| **Floor sections** | Floor_ID + Floor_Name on receipts | Single "Location" field | Section field |
| **Tax structure** | Separate GST (5%) for food, GST+PST (15%) for alcohol | Combined tax column | Combined tax |
| **Cuisine concept** | Pacific Northwest + Japanese fusion | West Coast / PNW | (varies) |
| **Period** | March 2026 (30 days) | February 2026 (28 days) | (varies) |

---

## Known Limitations & Intentional Gaps

1. **No split checks in this dataset.** `Parent_ID` and `Has_Children` fields are present but not exercised. Real Lightspeed data frequently has split checks.
2. **Delivery `POS_Transaction_ID` is blank.** Simulates a restaurant where delivery platforms are NOT integrated with the POS. Cross-referencing requires timestamp/amount matching.
3. **Reservation-to-POS linkage is implicit.** No direct join key. Matching requires fuzzy joins on date, time, party size, and server.
4. **Customer linkage is sparse.** ~45% of receipts have linked customers — realistic for restaurants without aggressive loyalty enrollment.
5. **Brunch items only on Sundays.** Menu availability changes by day.
6. **No Advanced Inventory / COGS tracking file.** COGS is embedded at the product level in `Lightspeed_06_products.csv` via the `Cost` column.
7. **Single payment per receipt.** This dataset uses one payment per receipt. Real data can have multiple payments (split tender) linked to a single receipt.
8. **Tax calculation is simplified.** BC tax rules for restaurants are complex (PST on alcohol, exempt on most prepared food consumed on premises). This dataset uses simplified rates.

---

*Generated by Food Factor data pipeline. Seed: 42 (reproducible).*
