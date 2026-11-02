"""
SQLite database manager and data access layer for Inventory Stock Tracker.
"""
from contextlib import contextmanager
import io
import csv
import sqlite3
import base64
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
import qrcode
from models import Item, StockMovement

DB_FILE = "inventory.db"

class DatabaseManager:
    def __init__(self, db_path: str = DB_FILE):
        self.db_path = db_path
        self.init_db()

    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
        finally:
            conn.close()

    def init_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Items table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sku TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    category TEXT NOT NULL DEFAULT 'General',
                    quantity INTEGER NOT NULL DEFAULT 0,
                    min_threshold INTEGER NOT NULL DEFAULT 5,
                    unit_cost REAL NOT NULL DEFAULT 0.0,
                    selling_price REAL NOT NULL DEFAULT 0.0,
                    supplier TEXT DEFAULT '',
                    location TEXT DEFAULT '',
                    description TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Stock Movements audit log table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS stock_movements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_id INTEGER NOT NULL,
                    movement_type TEXT NOT NULL CHECK(movement_type IN ('IN', 'OUT', 'ADJUSTMENT')),
                    quantity INTEGER NOT NULL,
                    previous_quantity INTEGER NOT NULL,
                    new_quantity INTEGER NOT NULL,
                    reason TEXT DEFAULT '',
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE
                )
            """)

            # Useful indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_items_sku ON items(sku)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_items_category ON items(category)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_movements_item ON stock_movements(item_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_movements_time ON stock_movements(timestamp DESC, id DESC)")
            conn.commit()

    def _row_to_item(self, row: sqlite3.Row) -> Item:
        return Item(
            id=row["id"],
            sku=row["sku"],
            name=row["name"],
            category=row["category"],
            quantity=row["quantity"],
            min_threshold=row["min_threshold"],
            unit_cost=row["unit_cost"],
            selling_price=row["selling_price"],
            supplier=row["supplier"] or "",
            location=row["location"] or "",
            description=row["description"] or "",
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"])
        )

    def add_item(self, item: Item) -> int:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO items (sku, name, category, quantity, min_threshold, unit_cost, selling_price, supplier, location, description, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                item.sku.strip().upper(),
                item.name.strip(),
                item.category.strip(),
                max(0, int(item.quantity)),
                max(0, int(item.min_threshold)),
                max(0.0, float(item.unit_cost)),
                max(0.0, float(item.selling_price)),
                item.supplier.strip(),
                item.location.strip(),
                item.description.strip(),
                now,
                now
            ))
            item_id = cursor.lastrowid
            
            # Initial stock movement record if quantity > 0
            if item.quantity > 0:
                cursor.execute("""
                    INSERT INTO stock_movements (item_id, movement_type, quantity, previous_quantity, new_quantity, reason, timestamp)
                    VALUES (?, 'IN', ?, 0, ?, 'Initial inventory stock', ?)
                """, (item_id, item.quantity, item.quantity, now))

            conn.commit()
            return item_id

    def update_item(self, item: Item) -> bool:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE items
                SET name = ?, category = ?, min_threshold = ?, unit_cost = ?,
                    selling_price = ?, supplier = ?, location = ?, description = ?, updated_at = ?
                WHERE id = ?
            """, (
                item.name.strip(),
                item.category.strip(),
                max(0, int(item.min_threshold)),
                max(0.0, float(item.unit_cost)),
                max(0.0, float(item.selling_price)),
                item.supplier.strip(),
                item.location.strip(),
                item.description.strip(),
                now,
                item.id
            ))
            conn.commit()
            return cursor.rowcount > 0

    def delete_item(self, item_id: int) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM items WHERE id = ?", (item_id,))
            conn.commit()
            return cursor.rowcount > 0

    def get_item_by_id(self, item_id: int) -> Optional[Item]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM items WHERE id = ?", (item_id,))
            row = cursor.fetchone()
            return self._row_to_item(row) if row else None

    def get_item_by_sku(self, sku: str) -> Optional[Item]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM items WHERE sku = ?", (sku.strip().upper(),))
            row = cursor.fetchone()
            return self._row_to_item(row) if row else None

    def get_all_items(self) -> List[Item]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM items ORDER BY name ASC")
            rows = cursor.fetchall()
            return [self._row_to_item(row) for row in rows]

    def search_items(self, query: str = "", category: str = "", status: str = "") -> List[Item]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            sql = "SELECT * FROM items WHERE 1=1"
            params = []

            if query:
                sql += " AND (sku LIKE ? OR name LIKE ? OR supplier LIKE ? OR location LIKE ?)"
                like_pattern = f"%{query}%"
                params.extend([like_pattern, like_pattern, like_pattern, like_pattern])

            if category and category.lower() != "all":
                sql += " AND category = ?"
                params.append(category)

            if status:
                if status == "OUT_OF_STOCK":
                    sql += " AND quantity <= 0"
                elif status == "LOW_STOCK":
                    sql += " AND quantity > 0 AND quantity <= min_threshold"
                elif status == "IN_STOCK":
                    sql += " AND quantity > min_threshold"

            sql += " ORDER BY name ASC"
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            return [self._row_to_item(row) for row in rows]

    def record_movement(self, item_id: int, movement_type: str, qty_change: int, reason: str = "") -> Tuple[bool, str, Optional[int]]:
        """
        Record a stock movement transaction:
        movement_type: 'IN', 'OUT', or 'ADJUSTMENT'
        For IN: adds qty_change to existing quantity
        For OUT: deducts qty_change from existing quantity (cannot drop below 0)
        For ADJUSTMENT: sets absolute quantity to qty_change, or applies delta
        """
        movement_type = movement_type.upper()
        if movement_type not in ('IN', 'OUT', 'ADJUSTMENT'):
            return False, f"Invalid movement type: {movement_type}", None

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT quantity, name, sku FROM items WHERE id = ?", (item_id,))
            row = cursor.fetchone()
            if not row:
                return False, f"Item ID {item_id} not found", None

            current_qty = row["quantity"]
            if movement_type == 'IN':
                if qty_change <= 0:
                    return False, "Quantity to add must be positive", None
                new_qty = current_qty + qty_change
                delta_recorded = qty_change
            elif movement_type == 'OUT':
                if qty_change <= 0:
                    return False, "Quantity to deduct must be positive", None
                if current_qty < qty_change:
                    return False, f"Insufficient stock! Available: {current_qty}, Requested: {qty_change}", None
                new_qty = current_qty - qty_change
                delta_recorded = qty_change
            else: # ADJUSTMENT
                # qty_change represents the exact verified physical count
                new_qty = max(0, qty_change)
                delta_recorded = abs(new_qty - current_qty)

            # Update item table
            cursor.execute("""
                UPDATE items SET quantity = ?, updated_at = ? WHERE id = ?
            """, (new_qty, now, item_id))

            # Insert stock movement audit log
            cursor.execute("""
                INSERT INTO stock_movements (item_id, movement_type, quantity, previous_quantity, new_quantity, reason, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (item_id, movement_type, delta_recorded, current_qty, new_qty, reason, now))

            conn.commit()
            return True, f"Stock updated successfully. New quantity: {new_qty}", new_qty

    def get_stock_movements(self, limit: int = 50, item_id: Optional[int] = None) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            sql = """
                SELECT sm.*, i.sku as item_sku, i.name as item_name
                FROM stock_movements sm
                JOIN items i ON sm.item_id = i.id
            """
            params = []
            if item_id:
                sql += " WHERE sm.item_id = ?"
                params.append(item_id)
            sql += " ORDER BY sm.timestamp DESC, sm.id DESC LIMIT ?"
            params.append(limit)

            cursor.execute(sql, params)
            rows = cursor.fetchall()
            movements = []
            for r in rows:
                movements.append({
                    "id": r["id"],
                    "item_id": r["item_id"],
                    "item_sku": r["item_sku"],
                    "item_name": r["item_name"],
                    "movement_type": r["movement_type"],
                    "quantity": r["quantity"],
                    "previous_quantity": r["previous_quantity"],
                    "new_quantity": r["new_quantity"],
                    "reason": r["reason"] or "",
                    "timestamp": str(r["timestamp"])
                })
            return movements

    def get_summary_statistics(self) -> Dict[str, Any]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_items,
                    COALESCE(SUM(quantity), 0) as total_units,
                    COALESCE(SUM(quantity * unit_cost), 0) as total_inventory_cost,
                    COALESCE(SUM(quantity * selling_price), 0) as total_inventory_retail,
                    COALESCE(SUM(CASE WHEN quantity <= 0 THEN 1 ELSE 0 END), 0) as out_of_stock_count,
                    COALESCE(SUM(CASE WHEN quantity > 0 AND quantity <= min_threshold THEN 1 ELSE 0 END), 0) as low_stock_count
                FROM items
            """)
            stats = dict(cursor.fetchone())

            # Category breakdown
            cursor.execute("""
                SELECT category, COUNT(*) as count, SUM(quantity) as total_qty, ROUND(SUM(quantity * unit_cost), 2) as val
                FROM items
                GROUP BY category
                ORDER BY count DESC
            """)
            cat_rows = cursor.fetchall()
            categories = [{"category": r["category"], "count": r["count"], "total_qty": r["total_qty"], "value": r["val"] or 0.0} for r in cat_rows]

            # Recent movements count
            cursor.execute("SELECT COUNT(*) FROM stock_movements")
            total_movements = cursor.fetchone()[0]

            stats["categories"] = categories
            stats["total_movements"] = total_movements
            stats["total_inventory_cost"] = round(stats["total_inventory_cost"], 2)
            stats["total_inventory_retail"] = round(stats["total_inventory_retail"], 2)
            stats["potential_profit"] = round(stats["total_inventory_retail"] - stats["total_inventory_cost"], 2)
            return stats

    def get_categories(self) -> List[str]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT category FROM items ORDER BY category ASC")
            return [r[0] for r in cursor.fetchall() if r[0]]

    def generate_qr_code_base64(self, sku: str) -> str:
        """Generate base64 encoded PNG of QR code for item SKU"""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=6,
            border=2,
        )
        qr.add_data(sku)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode("utf-8")

    def export_items_csv(self) -> str:
        items = self.get_all_items()
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "SKU", "Name", "Category", "Quantity", "Min_Threshold",
            "Unit_Cost", "Selling_Price", "Total_Cost_Value", "Total_Retail_Value",
            "Status", "Supplier", "Location", "Description"
        ])
        for it in items:
            writer.writerow([
                it.sku, it.name, it.category, it.quantity, it.min_threshold,
                it.unit_cost, it.selling_price, it.total_cost_value, it.total_retail_value,
                it.stock_status, it.supplier, it.location, it.description
            ])
        return output.getvalue()

    def import_items_csv(self, csv_content: str) -> Dict[str, Any]:
        """Import items from CSV string. Updates existing SKUs or inserts new."""
        reader = csv.DictReader(io.StringIO(csv_content))
        added_count = 0
        updated_count = 0
        errors = []

        for row_num, row in enumerate(reader, start=2):
            try:
                sku = row.get("SKU", "").strip().upper()
                name = row.get("Name", "").strip()
                if not sku or not name:
                    errors.append(f"Row {row_num}: SKU and Name are required.")
                    continue

                category = row.get("Category", "General").strip() or "General"
                quantity = int(row.get("Quantity", 0))
                min_threshold = int(row.get("Min_Threshold", 5))
                unit_cost = float(row.get("Unit_Cost", 0.0))
                selling_price = float(row.get("Selling_Price", 0.0))
                supplier = row.get("Supplier", "").strip()
                location = row.get("Location", "").strip()
                description = row.get("Description", "").strip()

                existing = self.get_item_by_sku(sku)
                if existing:
                    existing.name = name
                    existing.category = category
                    existing.min_threshold = min_threshold
                    existing.unit_cost = unit_cost
                    existing.selling_price = selling_price
                    existing.supplier = supplier
                    existing.location = location
                    existing.description = description
                    self.update_item(existing)
                    if existing.quantity != quantity:
                        self.record_movement(existing.id, 'ADJUSTMENT', quantity, "CSV import quantity sync")
                    updated_count += 1
                else:
                    new_item = Item(
                        sku=sku,
                        name=name,
                        category=category,
                        quantity=quantity,
                        min_threshold=min_threshold,
                        unit_cost=unit_cost,
                        selling_price=selling_price,
                        supplier=supplier,
                        location=location,
                        description=description
                    )
                    self.add_item(new_item)
                    added_count += 1
            except Exception as e:
                errors.append(f"Row {row_num}: {str(e)}")

        return {
            "added": added_count,
            "updated": updated_count,
            "errors": errors
        }
