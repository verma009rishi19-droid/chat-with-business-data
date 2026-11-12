"""Synthetic Data Generator for Blinkit-style Quick-Commerce Analytics.

Generates realistic relational data (~12,500 orders over 12 months)
with seeded operational trends and anomalies matching /docs_kb business notices.
"""

from __future__ import annotations

import csv
import random
from datetime import datetime, timedelta
from pathlib import Path


def generate_dataset(output_dir: Path | str | None = None, seed: int = 42) -> dict[str, int]:
    """Generate complete quick commerce relational dataset with seeded anomalies."""
    if output_dir is None:
        output_dir = Path(__file__).resolve().parent
    else:
        output_dir = Path(output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)
    random.seed(seed)

    start_date = datetime(2025, 1, 1, 6, 0, 0)
    total_days = 365

    # 1. Categories
    categories = [
        {"category_id": "CAT-01", "category_name": "Fresh Produce", "department": "Perishables"},
        {"category_id": "CAT-02", "category_name": "Dairy & Eggs", "department": "Perishables"},
        {"category_id": "CAT-03", "category_name": "Bakery & Breads", "department": "Fresh Foods"},
        {"category_id": "CAT-04", "category_name": "Snacks & Munchies", "department": "Packaged Goods"},
        {"category_id": "CAT-05", "category_name": "Beverages & Cold Drinks", "department": "Packaged Goods"},
        {"category_id": "CAT-06", "category_name": "Confectionery & Sweets", "department": "Gifting & Treats"},
        {"category_id": "CAT-07", "category_name": "Premium Dry Fruits", "department": "Gifting & Treats"},
        {"category_id": "CAT-08", "category_name": "Instant Foods & Noodles", "department": "Packaged Goods"},
    ]

    # 2. Products (50 items)
    products = [
        # Fresh Produce
        {"product_id": "PROD-001", "category_id": "CAT-01", "product_name": "Fresh Tomato Hybrid 1kg", "sku": "SKU-PROD-001", "unit_price": 42.0, "cost_price": 28.0, "is_perishable": True},
        {"product_id": "PROD-002", "category_id": "CAT-01", "product_name": "Fresh Onion 1kg", "sku": "SKU-PROD-002", "unit_price": 38.0, "cost_price": 24.0, "is_perishable": True},
        {"product_id": "PROD-003", "category_id": "CAT-01", "product_name": "Potato Fresh Crop 1kg", "sku": "SKU-PROD-003", "unit_price": 34.0, "cost_price": 20.0, "is_perishable": True},
        {"product_id": "PROD-004", "category_id": "CAT-01", "product_name": "Coriander Bunch 100g", "sku": "SKU-PROD-004", "unit_price": 14.0, "cost_price": 6.0, "is_perishable": True},
        {"product_id": "PROD-005", "category_id": "CAT-01", "product_name": "Baby Spinach Bunch 250g", "sku": "SKU-PROD-005", "unit_price": 28.0, "cost_price": 16.0, "is_perishable": True},
        {"product_id": "PROD-006", "category_id": "CAT-01", "product_name": "Fresh Lemon Pack of 4", "sku": "SKU-PROD-006", "unit_price": 25.0, "cost_price": 12.0, "is_perishable": True},
        {"product_id": "PROD-007", "category_id": "CAT-01", "product_name": "Imported Hass Avocados Twin Pack", "sku": "SKU-PROD-007", "unit_price": 249.0, "cost_price": 175.0, "is_perishable": True},
        {"product_id": "PROD-008", "category_id": "CAT-01", "product_name": "Shimla Apple Royal Gala 500g", "sku": "SKU-PROD-008", "unit_price": 120.0, "cost_price": 85.0, "is_perishable": True},
        {"product_id": "PROD-009", "category_id": "CAT-01", "product_name": "Banana Robusta 1kg", "sku": "SKU-PROD-009", "unit_price": 55.0, "cost_price": 35.0, "is_perishable": True},
        {"product_id": "PROD-010", "category_id": "CAT-01", "product_name": "Button Mushrooms 200g", "sku": "SKU-PROD-010", "unit_price": 55.0, "cost_price": 34.0, "is_perishable": True},
        # Dairy & Eggs
        {"product_id": "PROD-011", "category_id": "CAT-02", "product_name": "Organic Farm Fresh Whole Milk 1L", "sku": "SKU-DAI-001", "unit_price": 85.0, "cost_price": 64.0, "is_perishable": True},
        {"product_id": "PROD-012", "category_id": "CAT-02", "product_name": "Country Eggs Brown Pack of 6", "sku": "SKU-DAI-002", "unit_price": 75.0, "cost_price": 52.0, "is_perishable": True},
        {"product_id": "PROD-013", "category_id": "CAT-02", "product_name": "Standard Cow Milk Pouch 500ml", "sku": "SKU-DAI-003", "unit_price": 32.0, "cost_price": 26.0, "is_perishable": True},
        {"product_id": "PROD-014", "category_id": "CAT-02", "product_name": "Malai Fresh Paneer 200g", "sku": "SKU-DAI-004", "unit_price": 95.0, "cost_price": 70.0, "is_perishable": True},
        {"product_id": "PROD-015", "category_id": "CAT-02", "product_name": "Greek Yogurt Natural 400g", "sku": "SKU-DAI-005", "unit_price": 125.0, "cost_price": 88.0, "is_perishable": True},
        {"product_id": "PROD-016", "category_id": "CAT-02", "product_name": "Salted Table Butter 100g", "sku": "SKU-DAI-006", "unit_price": 58.0, "cost_price": 46.0, "is_perishable": True},
        # Bakery & Breads
        {"product_id": "PROD-017", "category_id": "CAT-03", "product_name": "Artisanal Sourdough Country Loaf 400g", "sku": "SKU-BAK-001", "unit_price": 140.0, "cost_price": 85.0, "is_perishable": True},
        {"product_id": "PROD-018", "category_id": "CAT-03", "product_name": "Whole Wheat Brown Bread 400g", "sku": "SKU-BAK-002", "unit_price": 50.0, "cost_price": 32.0, "is_perishable": True},
        {"product_id": "PROD-019", "category_id": "CAT-03", "product_name": "Multi-Grain Sandwich Bread 400g", "sku": "SKU-BAK-003", "unit_price": 55.0, "cost_price": 36.0, "is_perishable": True},
        {"product_id": "PROD-020", "category_id": "CAT-03", "product_name": "Olive & Rosemary Sourdough 400g", "sku": "SKU-BAK-004", "unit_price": 160.0, "cost_price": 95.0, "is_perishable": True},
        {"product_id": "PROD-021", "category_id": "CAT-03", "product_name": "Butter Croissant Twin Pack", "sku": "SKU-BAK-005", "unit_price": 130.0, "cost_price": 80.0, "is_perishable": True},
        # Snacks & Munchies
        {"product_id": "PROD-022", "category_id": "CAT-04", "product_name": "Salted Kettle Potato Chips 115g", "sku": "SKU-SNK-001", "unit_price": 60.0, "cost_price": 38.0, "is_perishable": False},
        {"product_id": "PROD-023", "category_id": "CAT-04", "product_name": "Spicy Peri-Peri Nachos 150g", "sku": "SKU-SNK-002", "unit_price": 75.0, "cost_price": 48.0, "is_perishable": False},
        {"product_id": "PROD-024", "category_id": "CAT-04", "product_name": "Roasted Salted Makhana 80g", "sku": "SKU-SNK-003", "unit_price": 110.0, "cost_price": 72.0, "is_perishable": False},
        {"product_id": "PROD-025", "category_id": "CAT-04", "product_name": "Classic Salted Peanuts 200g", "sku": "SKU-SNK-004", "unit_price": 45.0, "cost_price": 28.0, "is_perishable": False},
        # Beverages
        {"product_id": "PROD-026", "category_id": "CAT-05", "product_name": "Cold Pressed Valencia Orange Juice 250ml", "sku": "SKU-BEV-001", "unit_price": 99.0, "cost_price": 62.0, "is_perishable": True},
        {"product_id": "PROD-027", "category_id": "CAT-05", "product_name": "Sparkling Tonic Water Can 300ml", "sku": "SKU-BEV-002", "unit_price": 60.0, "cost_price": 35.0, "is_perishable": False},
        {"product_id": "PROD-028", "category_id": "CAT-05", "product_name": "Tender Coconut Water 200ml", "sku": "SKU-BEV-003", "unit_price": 50.0, "cost_price": 30.0, "is_perishable": True},
        {"product_id": "PROD-029", "category_id": "CAT-05", "product_name": "Instant Cold Brew Black Coffee 200ml", "sku": "SKU-BEV-004", "unit_price": 110.0, "cost_price": 68.0, "is_perishable": False},
        {"product_id": "PROD-030", "category_id": "CAT-05", "product_name": "Almond Milk Unsweetened 1L", "sku": "SKU-BEV-005", "unit_price": 240.0, "cost_price": 165.0, "is_perishable": False},
        # Confectionery & Sweets
        {"product_id": "PROD-031", "category_id": "CAT-06", "product_name": "Kaju Katli Heritage Gold Box 400g", "sku": "SKU-SWT-001", "unit_price": 420.0, "cost_price": 280.0, "is_perishable": True},
        {"product_id": "PROD-032", "category_id": "CAT-06", "product_name": "Motichoor Laddu Ghee Box 400g", "sku": "SKU-SWT-002", "unit_price": 280.0, "cost_price": 180.0, "is_perishable": True},
        {"product_id": "PROD-033", "category_id": "CAT-06", "product_name": "Dark Chocolate 70% Single Origin 80g", "sku": "SKU-SWT-003", "unit_price": 185.0, "cost_price": 115.0, "is_perishable": False},
        {"product_id": "PROD-034", "category_id": "CAT-06", "product_name": "Gulab Jamun Tin 1kg", "sku": "SKU-SWT-004", "unit_price": 260.0, "cost_price": 170.0, "is_perishable": False},
        # Premium Dry Fruits
        {"product_id": "PROD-035", "category_id": "CAT-07", "product_name": "California Almonds Jumbo 500g", "sku": "SKU-DRY-001", "unit_price": 490.0, "cost_price": 360.0, "is_perishable": False},
        {"product_id": "PROD-036", "category_id": "CAT-07", "product_name": "Royal Afghan Mixed Dry Fruits 500g", "sku": "SKU-DRY-002", "unit_price": 650.0, "cost_price": 480.0, "is_perishable": False},
        {"product_id": "PROD-037", "category_id": "CAT-07", "product_name": "Whole Cashews W240 Grade 500g", "sku": "SKU-DRY-003", "unit_price": 540.0, "cost_price": 410.0, "is_perishable": False},
        {"product_id": "PROD-038", "category_id": "CAT-07", "product_name": "Kashmiri Walnut Kernels 250g", "sku": "SKU-DRY-004", "unit_price": 390.0, "cost_price": 270.0, "is_perishable": False},
        {"product_id": "PROD-039", "category_id": "CAT-07", "product_name": "Roasted Salted Pistachios 200g", "sku": "SKU-DRY-005", "unit_price": 320.0, "cost_price": 230.0, "is_perishable": False},
        # Instant Foods
        {"product_id": "PROD-040", "category_id": "CAT-08", "product_name": "Korean Spicy Ramen Pack of 4", "sku": "SKU-INS-001", "unit_price": 199.0, "cost_price": 130.0, "is_perishable": False},
        {"product_id": "PROD-041", "category_id": "CAT-08", "product_name": "Classic Masala Oats 400g", "sku": "SKU-INS-002", "unit_price": 95.0, "cost_price": 65.0, "is_perishable": False},
        {"product_id": "PROD-042", "category_id": "CAT-08", "product_name": "Instant Ready-to-Cook Poha 200g", "sku": "SKU-INS-003", "unit_price": 45.0, "cost_price": 28.0, "is_perishable": False},
    ]

    # 3. Dark Stores (10 stores)
    dark_stores = [
        {"store_id": "STR-MUM-01", "store_name": "Bandra West Pod", "city": "Mumbai", "zone": "West", "hourly_capacity": 150},
        {"store_id": "STR-MUM-02", "store_name": "Andheri East Pod", "city": "Mumbai", "zone": "West", "hourly_capacity": 180},
        {"store_id": "STR-MUM-03", "store_name": "Colaba Heritage Pod", "city": "Mumbai", "zone": "South", "hourly_capacity": 110},
        {"store_id": "STR-DEL-01", "store_name": "Connaught Place Pod", "city": "Delhi-NCR", "zone": "Central", "hourly_capacity": 160},
        {"store_id": "STR-DEL-02", "store_name": "Gurgaon DLF CyberPod", "city": "Delhi-NCR", "zone": "South", "hourly_capacity": 200},
        {"store_id": "STR-DEL-03", "store_name": "Noida Sector 62 Pod", "city": "Delhi-NCR", "zone": "East", "hourly_capacity": 140},
        {"store_id": "STR-BLR-01", "store_name": "Indiranagar 100ft Pod", "city": "Bengaluru", "zone": "East", "hourly_capacity": 190},
        {"store_id": "STR-BLR-02", "store_name": "Koramangala 4th Block Pod", "city": "Bengaluru", "zone": "South", "hourly_capacity": 175},
        {"store_id": "STR-BLR-03", "store_name": "HSR Layout Sector 2 Pod", "city": "Bengaluru", "zone": "South-East", "hourly_capacity": 165},
        {"store_id": "STR-PUN-01", "store_name": "Koregaon Park Pod", "city": "Pune", "zone": "East", "hourly_capacity": 130},
    ]

    # 4. Customers (1,200 customers)
    first_names = ["Aarav", "Vivaan", "Aditya", "Vihaan", "Arjun", "Sai", "Reyansh", "Ayaan", "Krishna", "Ishaan",
                   "Diya", "Saanvi", "Ananya", "Aadhya", "Pari", "Chiara", "Riya", "Myra", "Anvi", "Fatima",
                   "Kavya", "Tara", "Rohan", "Meera", "Pooja", "Vikram", "Neha", "Rahul", "Priya", "Nikhil"]
    last_names = ["Sharma", "Verma", "Patel", "Mehta", "Iyer", "Nair", "Reddy", "Rao", "Deshmukh", "Kulkarni",
                  "Gupta", "Joshi", "Bhat", "Chopra", "Singh", "Kapoor", "Chatterjee", "Sen", "Menon", "Malhotra"]
    cities = ["Mumbai", "Delhi-NCR", "Bengaluru", "Pune"]
    tiers = ["Standard", "Silver", "Gold", "VIP"]
    tier_weights = [0.55, 0.25, 0.15, 0.05]

    customers = []
    for c_idx in range(1, 1201):
        signup_offset = random.randint(0, 300)
        signup_dt = (start_date + timedelta(days=signup_offset)).date()
        customers.append({
            "customer_id": f"CUST-{c_idx:04d}",
            "customer_name": f"{random.choice(first_names)} {random.choice(last_names)}",
            "city": random.choice(cities),
            "signup_date": signup_dt.isoformat(),
            "customer_tier": random.choices(tiers, weights=tier_weights)[0],
        })

    # 5. Inventory
    inventory = []
    inv_id = 1
    for store in dark_stores:
        for prod in products:
            base_stock = random.randint(40, 150)
            # Sourdough low stock in Q3 or dry fruit low stock in Diwali
            inventory.append({
                "inventory_id": f"INV-{inv_id:05d}",
                "store_id": store["store_id"],
                "product_id": prod["product_id"],
                "stock_on_hand": base_stock,
                "reorder_level": 25,
                "last_restocked_at": "2025-11-20 04:30:00",
            })
            inv_id += 1

    # 6. Orders, Order Items, Deliveries & Ratings
    orders = []
    order_items = []
    deliveries = []
    customer_ratings = []

    order_counter = 1
    item_counter = 1
    rating_counter = 1

    product_map = {p["product_id"]: p for p in products}

    # Generate ~12,500 orders across 365 days
    for day in range(total_days):
        current_day_date = start_date + timedelta(days=day)
        month = current_day_date.month
        day_of_month = current_day_date.day

        # Base daily order volume: ~30-40 orders per day
        # Festive season boost in Oct (Diwali) and Nov:
        if month in (10, 11):
            daily_orders_count = random.randint(45, 65)
        elif month in (7, 8):
            # Monsoon dip slightly in volume
            daily_orders_count = random.randint(28, 38)
        else:
            daily_orders_count = random.randint(30, 42)

        for _ in range(daily_orders_count):
            order_id = f"ORD-{order_counter:06d}"
            customer = random.choice(customers)
            # Match customer city with appropriate store if possible
            matching_stores = [s for s in dark_stores if s["city"] == customer["city"]]
            store = random.choice(matching_stores) if matching_stores else random.choice(dark_stores)

            hour = random.choices([7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22],
                                  weights=[5, 9, 8, 5, 4, 5, 4, 3, 3, 4, 6, 9, 12, 10, 8, 5])[0]
            minute = random.randint(0, 59)
            second = random.randint(0, 59)
            order_ts = current_day_date.replace(hour=hour, minute=minute, second=second)

            # Seeded Anomalies logic for items selection:
            # 1. Artisanal Sourdough & Olive Sourdough (PROD-017, PROD-020):
            #    Normal in Q1/Q2 (~15% chance in basket), drops by 80% in Q3 (July-Sept, month 7, 8, 9).
            # 2. Hass Avocados (PROD-007):
            #    Normal until mid-Aug, sharp 85% drop from Aug 15 to Sept 30 (month 8 day >= 15 to month 9).
            # 3. Organic Farm Milk (PROD-011):
            #    Surges starting May (month >= 5) by 140% weight.
            # 4. Festive Dry Fruits & Sweets (PROD-031, PROD-036):
            #    Massive surge in October (Diwali) and early November.

            # Determine candidate items
            basket_size = random.choices([1, 2, 3, 4, 5, 6], weights=[15, 30, 25, 15, 10, 5])[0]
            sampled_products = []

            # Determine weights for each product for today
            weights = []
            for p in products:
                pid = p["product_id"]
                w = 1.0

                # Trend 1: Sourdough Q3 recall
                if pid in ("PROD-017", "PROD-020"):
                    if month in (7, 8, 9):
                        w = 0.12  # 88% reduction due to recall
                    else:
                        w = 1.2

                # Trend 2: Hass Avocado cold chain breakdown
                elif pid == "PROD-007":
                    if (month == 8 and day_of_month >= 15) or (month == 9):
                        w = 0.08  # 92% drop
                    else:
                        w = 1.1

                # Trend 3: Organic Milk campaign boost starting May
                elif pid == "PROD-011":
                    if month >= 5:
                        w = 2.4
                    else:
                        w = 1.0

                # Trend 4: Festive dry fruits & sweets in Oct-Nov
                elif pid in ("PROD-031", "PROD-032", "PROD-035", "PROD-036"):
                    if month in (10, 11):
                        w = 4.2
                    else:
                        w = 0.7

                weights.append(w)

            chosen_prods = random.choices(products, weights=weights, k=basket_size)
            # Deduplicate within basket
            unique_chosen_prods = {p["product_id"]: p for p in chosen_prods}.values()

            order_subtotal = 0.0
            for cp in unique_chosen_prods:
                qty = random.choices([1, 2, 3], weights=[80, 15, 5])[0]
                # High quantity dry fruit hampers during Diwali
                if cp["product_id"] in ("PROD-031", "PROD-036") and month in (10, 11):
                    qty = random.choices([1, 2, 4], weights=[40, 40, 20])[0]

                item_total = round(qty * cp["unit_price"], 2)
                order_subtotal += item_total

                order_items.append({
                    "item_id": f"ITEM-{item_counter:07d}",
                    "order_id": order_id,
                    "product_id": cp["product_id"],
                    "quantity": qty,
                    "unit_price": cp["unit_price"],
                    "total_price": item_total,
                })
                item_counter += 1

                # Generate Product Rating on ~15% of items
                if random.random() < 0.15:
                    rating_score = random.choices([5, 4, 3, 2, 1], weights=[60, 25, 8, 4, 3])[0]
                    tag = "Quality"
                    comment = "Fresh and good."

                    # Specific negative feedback for avocados during August/Sept
                    if cp["product_id"] == "PROD-007" and ((month == 8 and day_of_month >= 15) or month == 9):
                        rating_score = random.choice([1, 2])
                        tag = "Spoiled / Overripe"
                        comment = "Avocados were completely brown inside and smelled fermenting."
                    elif cp["product_id"] == "PROD-017" and month in (7, 8):
                        rating_score = random.choice([1, 2])
                        tag = "Quality Issue"
                        comment = "Sour odor and dry crust. Usually love this bread, what happened?"

                    customer_ratings.append({
                        "rating_id": f"RAT-{rating_counter:06d}",
                        "order_id": order_id,
                        "product_id": cp["product_id"],
                        "rating_score": rating_score,
                        "feedback_tag": tag,
                        "comment": comment,
                    })
                    rating_counter += 1

            delivery_fee = 0.0 if order_subtotal > 299 else 15.0
            order_total = round(order_subtotal + delivery_fee, 2)
            payment_method = random.choices(["UPI", "Credit Card", "Net Banking", "Cash on Delivery"],
                                           weights=[68, 20, 6, 6])[0]

            # Cancellation rate: normally 2%, but in July-Aug in Mumbai/Delhi climbs to ~9%
            is_monsoon_delhi_mumbai = (month in (7, 8)) and (store["city"] in ("Mumbai", "Delhi-NCR"))
            if is_monsoon_delhi_mumbai and random.random() < 0.08:
                order_status = "Cancelled"
            else:
                order_status = "Delivered"

            orders.append({
                "order_id": order_id,
                "customer_id": customer["customer_id"],
                "store_id": store["store_id"],
                "order_status": order_status,
                "order_timestamp": order_ts.strftime("%Y-%m-%d %H:%M:%S"),
                "delivery_fee": delivery_fee,
                "total_amount": order_total,
                "payment_method": payment_method,
            })

            # Delivery details
            dispatch_offset_mins = random.randint(3, 7)
            dispatch_time = order_ts + timedelta(minutes=dispatch_offset_mins)

            weather = "Clear"
            if is_monsoon_delhi_mumbai:
                weather = random.choices(["Heavy Rain", "Thunderstorm", "Overcast", "Clear"],
                                         weights=[45, 25, 20, 10])[0]

            if weather in ("Heavy Rain", "Thunderstorm"):
                # Seeded anomaly: Delivery duration spikes to 30-55 mins
                duration_mins = round(random.uniform(28.0, 52.0), 1)
                delay_mins = max(0.0, round(duration_mins - 15.0, 1))
                del_rating = random.choices([1, 2, 3, 4], weights=[35, 35, 20, 10])[0]
            else:
                duration_mins = round(random.uniform(9.0, 16.0), 1)
                delay_mins = max(0.0, round(duration_mins - 15.0, 1))
                del_rating = random.choices([5, 4, 3], weights=[75, 20, 5])[0]

            if order_status == "Cancelled":
                delivery_time_str = ""
                duration_val = None
                del_rating = None
            else:
                delivery_time_dt = dispatch_time + timedelta(minutes=duration_mins)
                delivery_time_str = delivery_time_dt.strftime("%Y-%m-%d %H:%M:%S")
                duration_val = duration_mins

            deliveries.append({
                "delivery_id": f"DEL-{order_counter:06d}",
                "order_id": order_id,
                "rider_id": f"RDR-{random.randint(101, 220):03d}",
                "dispatch_time": dispatch_time.strftime("%Y-%m-%d %H:%M:%S"),
                "delivery_time": delivery_time_str,
                "delivery_duration_minutes": duration_val,
                "delay_minutes": delay_mins,
                "weather_condition": weather,
                "delivery_rating": del_rating,
            })

            order_counter += 1

    # Save to CSV files
    tables_to_dump = [
        ("categories.csv", categories),
        ("products.csv", products),
        ("dark_stores.csv", dark_stores),
        ("customers.csv", customers),
        ("orders.csv", orders),
        ("order_items.csv", order_items),
        ("deliveries.csv", deliveries),
        ("inventory.csv", inventory),
        ("customer_ratings.csv", customer_ratings),
    ]

    counts = {}
    for filename, data in tables_to_dump:
        file_path = output_dir / filename
        if data:
            keys = data[0].keys()
            with open(file_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=keys)
                writer.writeheader()
                writer.writerows(data)
        counts[filename] = len(data)

    return counts


if __name__ == "__main__":
    generated_counts = generate_dataset()
    print("Synthetic dataset successfully generated:")
    for fn, count in generated_counts.items():
        print(f"  - {fn}: {count:,} rows")
