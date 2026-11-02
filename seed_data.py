"""
Seed sample inventory data for demo and initial use.
"""
from database import DatabaseManager
from models import Item

def seed_sample_inventory(db: DatabaseManager = None):
    if db is None:
        db = DatabaseManager()

    # Don't seed if there is already data
    existing = db.get_all_items()
    if existing:
        print(f"Database already contains {len(existing)} items. Skipping seed.")
        return

    sample_items = [
        Item(
            sku="ELEC-LAP-001",
            name="ProBook 15 Laptop (Intel i7, 16GB RAM)",
            category="Electronics",
            quantity=18,
            min_threshold=5,
            unit_cost=650.00,
            selling_price=899.99,
            supplier="TechDistro Global",
            location="Aisle 1-A",
            description="15.6 inch high performance laptop for business and developer use."
        ),
        Item(
            sku="ELEC-MOU-002",
            name="Wireless Ergonomic Mouse",
            category="Electronics",
            quantity=4,
            min_threshold=10,
            unit_cost=15.50,
            selling_price=29.99,
            supplier="LogiSupply Corp",
            location="Aisle 1-B",
            description="Rechargeable optical mouse with silent click switches."
        ),
        Item(
            sku="ELEC-KEY-003",
            name="Mechanical Gaming Keyboard RGB",
            category="Electronics",
            quantity=0,
            min_threshold=5,
            unit_cost=42.00,
            selling_price=79.50,
            supplier="LogiSupply Corp",
            location="Aisle 1-C",
            description="Hot-swappable mechanical keyboard with blue switches."
        ),
        Item(
            sku="OFF-PAP-101",
            name="Multipurpose Copy Paper A4 (500 Sheets)",
            category="Office Supplies",
            quantity=85,
            min_threshold=20,
            unit_cost=3.20,
            selling_price=6.50,
            supplier="OfficeMax Ltd",
            location="Aisle 2-A",
            description="80gsm bright white printing paper for laser and inkjet."
        ),
        Item(
            sku="OFF-PEN-102",
            name="Gel Ink Pens 0.7mm (Box of 12)",
            category="Office Supplies",
            quantity=6,
            min_threshold=8,
            unit_cost=4.50,
            selling_price=9.99,
            supplier="Stationery World",
            location="Aisle 2-B",
            description="Smooth writing black ink rollerball pens."
        ),
        Item(
            sku="APP-TSH-201",
            name="Cotton Crewneck T-Shirt (Navy Blue, L)",
            category="Apparel",
            quantity=45,
            min_threshold=15,
            unit_cost=8.00,
            selling_price=19.99,
            supplier="Urban Weave Co",
            location="Rack 3-B",
            description="100% combed organic cotton breathable t-shirt."
        ),
        Item(
            sku="APP-HOO-202",
            name="Fleece Pullover Hoodie (Heather Grey, M)",
            category="Apparel",
            quantity=2,
            min_threshold=10,
            unit_cost=18.00,
            selling_price=39.99,
            supplier="Urban Weave Co",
            location="Rack 3-D",
            description="Soft fleece hoodie with kangaroo pocket."
        ),
        Item(
            sku="TOOL-DRL-301",
            name="Cordless Hammer Drill 20V",
            category="Tools & Hardware",
            quantity=12,
            min_threshold=4,
            unit_cost=55.00,
            selling_price=109.00,
            supplier="Apex Industrial Tools",
            location="Bay 4-A",
            description="Brushless motor cordless drill with 2 lithium-ion batteries."
        ),
        Item(
            sku="TOOL-MET-302",
            name="Steel Measuring Tape (8m / 26ft)",
            category="Tools & Hardware",
            quantity=32,
            min_threshold=10,
            unit_cost=4.00,
            selling_price=11.50,
            supplier="Apex Industrial Tools",
            location="Bay 4-C",
            description="Shockproof heavy-duty tape measure with auto lock."
        ),
        Item(
            sku="GROC-COF-401",
            name="Organic Medium Roast Coffee Beans (1kg)",
            category="Groceries",
            quantity=3,
            min_threshold=8,
            unit_cost=11.20,
            selling_price=22.00,
            supplier="Andes Coffee Imports",
            location="Shelf 5-A",
            description="Single-origin Arabica whole coffee beans."
        ),
    ]

    print("Seeding sample inventory items...")
    for item in sample_items:
        item_id = db.add_item(item)
        print(f"  + Added: [{item.sku}] {item.name} (Qty: {item.quantity})")

    # Add a few realistic stock transactions
    print("Generating initial movement history...")
    mouse = db.get_item_by_sku("ELEC-MOU-002")
    if mouse:
        db.record_movement(mouse.id, "OUT", 6, "Shipped customer order #SO-1082")
    
    coffee = db.get_item_by_sku("GROC-COF-401")
    if coffee:
        db.record_movement(coffee.id, "OUT", 5, "Store pickup order #SO-1090")

    drill = db.get_item_by_sku("TOOL-DRL-301")
    if drill:
        db.record_movement(drill.id, "IN", 4, "Received restock PO #PO-4091")

    print("Seed complete! Inventory ready.")

if __name__ == "__main__":
    seed_sample_inventory()
