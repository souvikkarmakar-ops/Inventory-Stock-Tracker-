# 📦 Inventory Stock Tracker

A modern, full-featured **Inventory Stock Tracker** built with Python, SQLite, Flask, and Rich. Designed for warehouses, retail shops, e-commerce managers, and small businesses to monitor stock levels, manage replenishment cycles, prevent stockouts, and audit historical inventory movements.

---

## 🌟 Key Features

### 🖥️ Interactive Web Dashboard
- **Live KPI Metrics**: Total catalog items, units on hand, total inventory cost valuation, potential retail revenue, and profit calculations.
- **Low Stock & Out-of-Stock Alerting**: Automatic calculation against reorder thresholds with real-time alert banners.
- **Stock Movements (Ledger)**:
  - 📥 **Stock IN**: Receive shipments and purchase orders.
  - 📤 **Stock OUT**: Dispatch customer orders and track sales.
  - 🔧 **Count Audit**: Adjust and reconcile physical inventory counts.
- **Dynamic Product Catalog**:
  - Filter by category and stock health (In Stock, Low Stock, Out of Stock).
  - Instant live debounced search across SKU, product name, supplier, and warehouse location.
- **QR Code & Barcode Integration**: Automatically generates scannable QR code labels for any item SKU with 1-click printable label views.
- **Visual Analytics**: Interactive Chart.js charts breaking down inventory valuation and unit quantities by category.
- **Bulk CSV Export & Import**:
  - 1-click full inventory export to CSV.
  - Bulk import with automatic SKU reconciliation and built-in downloadable template.

### 💻 Interactive Terminal CLI
- Powered by `rich` with colored tables, status badges, formatted panels, and user-friendly prompts.
- Perform quick stock adjustments, search items, view audit logs, and inspect financials straight from your command line.

### 🗄️ Robust Database & Architecture
- **ACID Transactions**: Atomic stock movements and updates.
- **Foreign Key Cascades & Indexes**: High-performance lookup on SKUs, categories, and chronological timestamps.
- **Auto-Seeding**: Comes pre-populated with realistic demo inventory across Electronics, Office Supplies, Apparel, Hardware, and Groceries.

---

## 📁 Project Structure

```
Inventory Stock Tracker/
├── app.py                 # Flask web server & REST API endpoints
├── cli.py                 # Interactive terminal CLI (Rich interface)
├── database.py            # SQLite database manager & data access layer
├── models.py              # Data models (Item, StockMovement)
├── seed_data.py           # Preloaded realistic sample inventory
├── test_inventory.py      # Automated unit & integration tests
├── requirements.txt       # Python project dependencies
├── README.md              # Project documentation
├── static/
│   ├── css/
│   │   └── style.css      # Modern dark-mode responsive styling
│   └── js/
│       └── app.js         # Frontend logic, charts, and API client
└── templates/
    └── index.html         # Web application dashboard
```

---

## 🚀 Quickstart Guide

### 1. Prerequisites
Python 3.10+ installed on your system.

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Launch the Web Application
Run the Flask server:
```bash
python app.py
```
Open your web browser and navigate to:
```
http://127.0.0.1:5000
```

### 4. Launch the Interactive Terminal CLI
Prefer using the terminal? Run:
```bash
python cli.py
```
Use the interactive numeric menu to navigate products, execute Stock IN / OUT movements, check low-stock alerts, and export reports.

---

## 🔌 REST API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/stats` | Retrieve dashboard KPI metrics and category analytics |
| `GET` | `/api/categories` | Retrieve list of distinct item categories |
| `GET` | `/api/items` | Query items with `query`, `category`, and `status` filters |
| `GET` | `/api/items/<id>` | Get item details, base64 QR code, and recent movement logs |
| `POST` | `/api/items` | Create a new inventory product |
| `PUT` | `/api/items/<id>` | Update an existing item's specifications |
| `DELETE` | `/api/items/<id>` | Permanently delete an item and its movement logs |
| `GET` | `/api/movements` | Retrieve chronological stock audit logs |
| `POST` | `/api/movements` | Record a stock movement (`IN`, `OUT`, or `ADJUSTMENT`) |
| `GET` | `/api/export/csv` | Download full inventory snapshot as a `.csv` file |
| `POST` | `/api/import/csv` | Bulk upload `.csv` to update or insert products |

---

## 🧪 Running Automated Tests

Run the test suite to verify database transactions, constraints, stock movement validations, and API routes:

```bash
python -m unittest test_inventory.py
```

All 7 unit and integration tests run in an isolated temporary environment.

---

## 📄 License
MIT License. Free to use, adapt, and build upon!
