"""
Data models and dataclasses for Inventory Stock Tracker.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class Item:
    id: Optional[int] = None
    sku: str = ""
    name: str = ""
    category: str = "General"
    quantity: int = 0
    min_threshold: int = 5
    unit_cost: float = 0.0
    selling_price: float = 0.0
    supplier: str = ""
    location: str = ""
    description: str = ""
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    @property
    def total_cost_value(self) -> float:
        return round(self.quantity * self.unit_cost, 2)

    @property
    def total_retail_value(self) -> float:
        return round(self.quantity * self.selling_price, 2)

    @property
    def is_low_stock(self) -> bool:
        return self.quantity <= self.min_threshold

    @property
    def is_out_of_stock(self) -> bool:
        return self.quantity <= 0

    @property
    def stock_status(self) -> str:
        if self.quantity <= 0:
            return "OUT_OF_STOCK"
        elif self.quantity <= self.min_threshold:
            return "LOW_STOCK"
        return "IN_STOCK"

    def to_dict(self):
        return {
            "id": self.id,
            "sku": self.sku,
            "name": self.name,
            "category": self.category,
            "quantity": self.quantity,
            "min_threshold": self.min_threshold,
            "unit_cost": self.unit_cost,
            "selling_price": self.selling_price,
            "total_cost_value": self.total_cost_value,
            "total_retail_value": self.total_retail_value,
            "supplier": self.supplier,
            "location": self.location,
            "description": self.description,
            "is_low_stock": self.is_low_stock,
            "is_out_of_stock": self.is_out_of_stock,
            "stock_status": self.stock_status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

@dataclass
class StockMovement:
    id: Optional[int] = None
    item_id: int = 0
    item_sku: str = ""
    item_name: str = ""
    movement_type: str = "IN"  # IN, OUT, ADJUSTMENT
    quantity: int = 0
    previous_quantity: int = 0
    new_quantity: int = 0
    reason: str = ""
    timestamp: Optional[str] = None

    def to_dict(self):
        return {
            "id": self.id,
            "item_id": self.item_id,
            "item_sku": self.item_sku,
            "item_name": self.item_name,
            "movement_type": self.movement_type,
            "quantity": self.quantity,
            "previous_quantity": self.previous_quantity,
            "new_quantity": self.new_quantity,
            "reason": self.reason,
            "timestamp": self.timestamp,
        }
