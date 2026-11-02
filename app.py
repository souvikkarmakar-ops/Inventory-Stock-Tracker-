"""
Flask Web Application & REST API for Inventory Stock Tracker.
"""
import os
import io
from flask import Flask, render_template, request, jsonify, Response, send_file
from database import DatabaseManager
from models import Item
from seed_data import seed_sample_inventory

app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False

db = DatabaseManager()
seed_sample_inventory(db)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/stats", methods=["GET"])
def get_stats():
    stats = db.get_summary_statistics()
    return jsonify(stats)

@app.route("/api/categories", methods=["GET"])
def get_categories():
    categories = db.get_categories()
    return jsonify(categories)

@app.route("/api/items", methods=["GET"])
def get_items():
    query = request.args.get("query", "").strip()
    category = request.args.get("category", "").strip()
    status = request.args.get("status", "").strip()

    items = db.search_items(query=query, category=category, status=status)
    return jsonify([item.to_dict() for item in items])

@app.route("/api/items/<int:item_id>", methods=["GET"])
def get_item(item_id):
    item = db.get_item_by_id(item_id)
    if not item:
        return jsonify({"error": "Item not found"}), 404

    item_dict = item.to_dict()
    # Add QR code image
    try:
        item_dict["qr_code"] = db.generate_qr_code_base64(item.sku)
    except Exception:
        item_dict["qr_code"] = None

    # Get recent item movements
    item_dict["movements"] = db.get_stock_movements(limit=10, item_id=item_id)
    return jsonify(item_dict)

@app.route("/api/items", methods=["POST"])
def add_item():
    data = request.get_json() or {}
    sku = str(data.get("sku", "")).strip().upper()
    name = str(data.get("name", "")).strip()

    if not sku:
        return jsonify({"error": "SKU code is required"}), 400
    if not name:
        return jsonify({"error": "Item name is required"}), 400

    existing = db.get_item_by_sku(sku)
    if existing:
        return jsonify({"error": f"Item with SKU '{sku}' already exists"}), 409

    try:
        quantity = int(data.get("quantity", 0))
        min_threshold = int(data.get("min_threshold", 5))
        unit_cost = float(data.get("unit_cost", 0.0))
        selling_price = float(data.get("selling_price", 0.0))
    except (ValueError, TypeError) as e:
        return jsonify({"error": f"Invalid numeric input: {str(e)}"}), 400

    item = Item(
        sku=sku,
        name=name,
        category=str(data.get("category", "General")).strip() or "General",
        quantity=quantity,
        min_threshold=min_threshold,
        unit_cost=unit_cost,
        selling_price=selling_price,
        supplier=str(data.get("supplier", "")).strip(),
        location=str(data.get("location", "")).strip(),
        description=str(data.get("description", "")).strip()
    )

    item_id = db.add_item(item)
    return jsonify({"success": True, "message": "Item added successfully", "id": item_id}), 201

@app.route("/api/items/<int:item_id>", methods=["PUT"])
def update_item(item_id):
    existing = db.get_item_by_id(item_id)
    if not existing:
        return jsonify({"error": "Item not found"}), 404

    data = request.get_json() or {}
    name = str(data.get("name", "")).strip()
    if not name:
        return jsonify({"error": "Item name is required"}), 400

    try:
        existing.name = name
        existing.category = str(data.get("category", "General")).strip() or "General"
        existing.min_threshold = int(data.get("min_threshold", 5))
        existing.unit_cost = float(data.get("unit_cost", 0.0))
        existing.selling_price = float(data.get("selling_price", 0.0))
        existing.supplier = str(data.get("supplier", "")).strip()
        existing.location = str(data.get("location", "")).strip()
        existing.description = str(data.get("description", "")).strip()
    except (ValueError, TypeError) as e:
        return jsonify({"error": f"Invalid numeric input: {str(e)}"}), 400

    success = db.update_item(existing)
    if success:
        return jsonify({"success": True, "message": "Item updated successfully"})
    return jsonify({"error": "Failed to update item"}), 500

@app.route("/api/items/<int:item_id>", methods=["DELETE"])
def delete_item(item_id):
    existing = db.get_item_by_id(item_id)
    if not existing:
        return jsonify({"error": "Item not found"}), 404

    success = db.delete_item(item_id)
    if success:
        return jsonify({"success": True, "message": f"Item '{existing.name}' deleted successfully"})
    return jsonify({"error": "Failed to delete item"}), 500

@app.route("/api/movements", methods=["GET"])
def get_movements():
    limit = request.args.get("limit", 50, type=int)
    item_id = request.args.get("item_id", type=int)
    movements = db.get_stock_movements(limit=limit, item_id=item_id)
    return jsonify(movements)

@app.route("/api/movements", methods=["POST"])
def record_movement():
    data = request.get_json() or {}
    item_id = data.get("item_id")
    movement_type = str(data.get("movement_type", "")).strip().upper()
    reason = str(data.get("reason", "")).strip()

    if not item_id:
        return jsonify({"error": "Item ID is required"}), 400

    try:
        quantity = int(data.get("quantity", 0))
    except (ValueError, TypeError):
        return jsonify({"error": "Quantity must be an integer"}), 400

    success, msg, new_qty = db.record_movement(item_id, movement_type, quantity, reason)
    if not success:
        return jsonify({"error": msg}), 400

    return jsonify({"success": True, "message": msg, "new_quantity": new_qty})

@app.route("/api/export/csv", methods=["GET"])
def export_csv():
    csv_string = db.export_items_csv()
    return Response(
        csv_string,
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=inventory_report.csv"}
    )

@app.route("/api/import/csv", methods=["POST"])
def import_csv():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    if not file.filename.endswith(".csv"):
        return jsonify({"error": "Uploaded file must be a .csv file"}), 400

    try:
        content = file.read().decode("utf-8")
        result = db.import_items_csv(content)
        return jsonify({
            "success": True,
            "message": f"Processed CSV: {result['added']} added, {result['updated']} updated.",
            "details": result
        })
    except Exception as e:
        return jsonify({"error": f"Failed to parse CSV: {str(e)}"}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"\n==========================================================")
    print(f"📦 Inventory Stock Tracker Web Application")
    print(f"🚀 Running locally on: http://127.0.0.1:{port}")
    print(f"==========================================================\n")
    app.run(host="127.0.0.1", port=port, debug=False)
