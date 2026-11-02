"""
Comprehensive unit and integration test suite for Inventory Stock Tracker.
"""
import os
import unittest
import tempfile
import json
import gc
from models import Item
from database import DatabaseManager
from app import app

class TestInventoryTracker(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for test isolation
        self.test_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.test_dir.name, "test_inventory.db")
        self.db = DatabaseManager(self.db_path)

        # Configure Flask test client
        app.config['TESTING'] = True
        self.client = app.test_client()

    def tearDown(self):
        # Explicit garbage collection to ensure sqlite connections are released on Windows
        del self.db
        gc.collect()
        try:
            self.test_dir.cleanup()
        except Exception:
            pass

    def test_add_and_get_item(self):
        item = Item(
            sku="TEST-SKU-001",
            name="Test Screwdriver Set",
            category="Tools",
            quantity=15,
            min_threshold=5,
            unit_cost=10.00,
            selling_price=19.99,
            supplier="ToolMaster Inc",
            location="Aisle 1",
            description="High precision set"
        )
        item_id = self.db.add_item(item)
        self.assertIsNotNone(item_id)

        fetched = self.db.get_item_by_id(item_id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.sku, "TEST-SKU-001")
        self.assertEqual(fetched.name, "Test Screwdriver Set")
        self.assertEqual(fetched.quantity, 15)
        self.assertEqual(fetched.unit_cost, 10.00)
        self.assertEqual(fetched.total_cost_value, 150.00)
        self.assertEqual(fetched.stock_status, "IN_STOCK")

    def test_stock_in_movement(self):
        item = Item(sku="IN-001", name="Item In", quantity=10, min_threshold=5)
        item_id = self.db.add_item(item)

        success, msg, new_qty = self.db.record_movement(item_id, "IN", 15, "Supplier replenishment")
        self.assertTrue(success)
        self.assertEqual(new_qty, 25)

        updated_item = self.db.get_item_by_id(item_id)
        self.assertEqual(updated_item.quantity, 25)

        # Check movement history
        movements = self.db.get_stock_movements(item_id=item_id)
        self.assertGreaterEqual(len(movements), 2)
        latest = movements[0]
        self.assertEqual(latest["movement_type"], "IN")
        self.assertEqual(latest["quantity"], 15)
        self.assertEqual(latest["previous_quantity"], 10)
        self.assertEqual(latest["new_quantity"], 25)

    def test_stock_out_movement_and_insufficient_stock(self):
        item = Item(sku="OUT-001", name="Item Out", quantity=10, min_threshold=5)
        item_id = self.db.add_item(item)

        # Successful stock out
        success, msg, new_qty = self.db.record_movement(item_id, "OUT", 4, "Customer sale")
        self.assertTrue(success)
        self.assertEqual(new_qty, 6)

        # Oversold stock out should be rejected
        success, msg, new_qty = self.db.record_movement(item_id, "OUT", 20, "Excessive sale")
        self.assertFalse(success)
        self.assertIn("Insufficient stock", msg)

        # Verify quantity did not change on failed stock out
        recheck = self.db.get_item_by_id(item_id)
        self.assertEqual(recheck.quantity, 6)

    def test_stock_adjustment_count(self):
        item = Item(sku="ADJ-001", name="Item Audit", quantity=10, min_threshold=5)
        item_id = self.db.add_item(item)

        success, msg, new_qty = self.db.record_movement(item_id, "ADJUSTMENT", 7, "Physical count audit")
        self.assertTrue(success)
        self.assertEqual(new_qty, 7)

        recheck = self.db.get_item_by_id(item_id)
        self.assertEqual(recheck.quantity, 7)

    def test_low_stock_and_out_of_stock_status(self):
        # Item 1: In stock
        self.db.add_item(Item(sku="ST-01", name="High Stock", quantity=50, min_threshold=10))
        # Item 2: Low stock
        self.db.add_item(Item(sku="ST-02", name="Low Stock", quantity=5, min_threshold=10))
        # Item 3: Out of stock
        self.db.add_item(Item(sku="ST-03", name="Zero Stock", quantity=0, min_threshold=10))

        low_stock_items = self.db.search_items(status="LOW_STOCK")
        out_stock_items = self.db.search_items(status="OUT_OF_STOCK")
        in_stock_items = self.db.search_items(status="IN_STOCK")

        self.assertEqual(len(low_stock_items), 1)
        self.assertEqual(low_stock_items[0].sku, "ST-02")

        self.assertEqual(len(out_stock_items), 1)
        self.assertEqual(out_stock_items[0].sku, "ST-03")

        self.assertEqual(len(in_stock_items), 1)
        self.assertEqual(in_stock_items[0].sku, "ST-01")

    def test_csv_export_and_import(self):
        self.db.add_item(Item(sku="CSV-01", name="CSV Product A", category="TestCat", quantity=20, unit_cost=5.0))
        csv_text = self.db.export_items_csv()
        self.assertIn("CSV-01", csv_text)
        self.assertIn("CSV Product A", csv_text)

        # Import new item via CSV string
        new_csv_content = (
            "SKU,Name,Category,Quantity,Min_Threshold,Unit_Cost,Selling_Price,Supplier,Location,Description\n"
            "CSV-NEW-99,Imported Widget,Hardware,33,8,12.00,22.50,SupplierX,Rack-9,Import test widget\n"
        )
        res = self.db.import_items_csv(new_csv_content)
        self.assertEqual(res["added"], 1)

        imported = self.db.get_item_by_sku("CSV-NEW-99")
        self.assertIsNotNone(imported)
        self.assertEqual(imported.quantity, 33)
        self.assertEqual(imported.name, "Imported Widget")

    def test_flask_api_endpoints(self):
        # Test stats
        res = self.client.get("/api/stats")
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertIn("total_items", data)
        self.assertIn("total_inventory_cost", data)

        # Test items list
        res = self.client.get("/api/items")
        self.assertEqual(res.status_code, 200)
        items = json.loads(res.data)
        self.assertIsInstance(items, list)

        # Test CSV export endpoint
        res = self.client.get("/api/export/csv")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.mimetype, "text/csv")

if __name__ == "__main__":
    unittest.main()
