"""
Interactive Terminal CLI for Inventory Stock Tracker using Rich.
"""
import sys
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, Confirm, IntPrompt, FloatPrompt
from rich.text import Text
from rich import box

from database import DatabaseManager
from models import Item

console = Console()
db = DatabaseManager()

def print_header():
    console.clear()
    banner = """
  ╔════════════════════════════════════════════════════════════════╗
  ║                 📦 INVENTORY STOCK TRACKER                     ║
  ║               Smart Warehouse & Stock Control                  ║
  ╚════════════════════════════════════════════════════════════════╝
    """
    console.print(f"[bold cyan]{banner}[/bold cyan]")

def display_summary():
    stats = db.get_summary_statistics()
    summary_text = (
        f"[bold]Total Catalog Items:[/bold] [yellow]{stats['total_items']}[/yellow]   │   "
        f"[bold]Total Units on Hand:[/bold] [cyan]{stats['total_units']}[/cyan]   │   "
        f"[bold]Total Cost Value:[/bold] [green]${stats['total_inventory_cost']:,.2f}[/green]   │   "
        f"[bold]Retail Value:[/bold] [green]${stats['total_inventory_retail']:,.2f}[/green]\n"
        f"[bold]Low Stock Alerts:[/bold] [bold red]{stats['low_stock_count']}[/bold red]   │   "
        f"[bold]Out of Stock:[/bold] [bold magenta]{stats['out_of_stock_count']}[/bold magenta]   │   "
        f"[bold]Stock Movement Logs:[/bold] [blue]{stats['total_movements']}[/blue]"
    )
    console.print(Panel(summary_text, title="📊 Quick Dashboard Summary", border_style="blue", expand=False))

def list_inventory_table(items=None, title="Current Inventory List"):
    if items is None:
        items = db.get_all_items()

    if not items:
        console.print("[yellow]No items found matching the criteria.[/yellow]")
        return

    table = Table(title=title, box=box.ROUNDED, show_lines=True, header_style="bold magenta")
    table.add_column("ID", justify="center", style="dim", width=4)
    table.add_column("SKU", style="bold cyan", width=14)
    table.add_column("Product Name", style="white", min_width=24)
    table.add_column("Category", style="blue")
    table.add_column("Stock", justify="right")
    table.add_column("Min", justify="right", style="dim")
    table.add_column("Unit Cost", justify="right")
    table.add_column("Selling Price", justify="right")
    table.add_column("Total Cost", justify="right", style="green")
    table.add_column("Status", justify="center")
    table.add_column("Location", style="dim")

    for item in items:
        if item.quantity <= 0:
            status_badge = "[bold white on red] OUT OF STOCK [/bold white on red]"
            stock_style = "bold red"
        elif item.quantity <= item.min_threshold:
            status_badge = "[bold black on yellow] LOW STOCK [/bold black on yellow]"
            stock_style = "bold yellow"
        else:
            status_badge = "[bold white on green] IN STOCK [/bold white on green]"
            stock_style = "bold green"

        table.add_row(
            str(item.id),
            item.sku,
            item.name,
            item.category,
            f"[{stock_style}]{item.quantity}[/{stock_style}]",
            str(item.min_threshold),
            f"${item.unit_cost:.2f}",
            f"${item.selling_price:.2f}",
            f"${item.total_cost_value:.2f}",
            status_badge,
            item.location or "-"
        )

    console.print(table)

def handle_stock_operation(op_type: str):
    sku = Prompt.ask("[bold cyan]Enter item SKU or ID[/bold cyan]").strip()
    item = None
    if sku.isdigit():
        item = db.get_item_by_id(int(sku))
    if not item:
        item = db.get_item_by_sku(sku)

    if not item:
        console.print(f"[red]Error: Item '{sku}' not found![/red]")
        return

    console.print(f"\nSelected: [bold]{item.name}[/bold] (SKU: [cyan]{item.sku}[/cyan]) | Current Stock: [bold yellow]{item.quantity}[/bold yellow]")

    if op_type == "IN":
        qty = IntPrompt.ask("Enter quantity to [bold green]ADD (Stock In)[/bold green]")
        reason = Prompt.ask("Reason / PO Number", default="Restock delivery")
        success, msg, new_qty = db.record_movement(item.id, "IN", qty, reason)
    elif op_type == "OUT":
        qty = IntPrompt.ask("Enter quantity to [bold red]REMOVE (Stock Out)[/bold red]")
        reason = Prompt.ask("Reason / Order ID", default="Customer sale")
        success, msg, new_qty = db.record_movement(item.id, "OUT", qty, reason)
    else:  # ADJUSTMENT
        qty = IntPrompt.ask("Enter verified physical count (Exact Count)")
        reason = Prompt.ask("Reason / Audit note", default="Physical audit reconciliation")
        success, msg, new_qty = db.record_movement(item.id, "ADJUSTMENT", qty, reason)

    if success:
        console.print(f"[bold green]✔ {msg}[/bold green]")
    else:
        console.print(f"[bold red]✘ {msg}[/bold red]")

def handle_add_item():
    console.print(Panel("➕ Add New Inventory Item", border_style="cyan"))
    sku = Prompt.ask("SKU Code (e.g. ELEC-001)").strip().upper()
    existing = db.get_item_by_sku(sku)
    if existing:
        console.print(f"[red]Error: An item with SKU '{sku}' already exists![/red]")
        return

    name = Prompt.ask("Product Name")
    category = Prompt.ask("Category", default="General")
    quantity = IntPrompt.ask("Initial Quantity", default=0)
    min_threshold = IntPrompt.ask("Minimum Stock Alert Threshold", default=5)
    unit_cost = FloatPrompt.ask("Unit Cost Price ($)", default=0.0)
    selling_price = FloatPrompt.ask("Selling / Retail Price ($)", default=0.0)
    supplier = Prompt.ask("Supplier Name (optional)", default="")
    location = Prompt.ask("Warehouse Location / Aisle (optional)", default="")
    description = Prompt.ask("Description (optional)", default="")

    item = Item(
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

    item_id = db.add_item(item)
    console.print(f"[bold green]✔ Item successfully added with ID #{item_id}![/bold green]")

def handle_search():
    query = Prompt.ask("Enter search query (SKU, Name, Supplier, or Location)")
    results = db.search_items(query=query)
    list_inventory_table(results, title=f"Search Results for '{query}'")

def handle_low_stock_alerts():
    items = db.search_items(status="LOW_STOCK")
    out_of_stock = db.search_items(status="OUT_OF_STOCK")
    critical_items = out_of_stock + items
    if not critical_items:
        console.print("[bold green]All items are healthy and above their reorder thresholds![/bold green]")
        return
    list_inventory_table(critical_items, title="⚠️ Low & Out of Stock Alert List")

def handle_view_movements():
    movements = db.get_stock_movements(limit=25)
    if not movements:
        console.print("[yellow]No stock movement transactions recorded yet.[/yellow]")
        return

    table = Table(title="📜 Recent Stock Movement Audit Logs (Last 25)", box=box.ROUNDED, header_style="bold cyan")
    table.add_column("Timestamp", style="dim", width=19)
    table.add_column("Type", justify="center")
    table.add_column("SKU", style="bold")
    table.add_column("Product", min_width=20)
    table.add_column("Change", justify="right")
    table.add_column("Before", justify="right")
    table.add_column("After", justify="right")
    table.add_column("Reason / Reference", style="italic")

    for m in movements:
        m_type = m["movement_type"]
        if m_type == "IN":
            type_badge = "[bold green]STOCK IN[/bold green]"
            change_str = f"[green]+{m['quantity']}[/green]"
        elif m_type == "OUT":
            type_badge = "[bold red]STOCK OUT[/bold red]"
            change_str = f"[red]-{m['quantity']}[/red]"
        else:
            type_badge = "[bold yellow]ADJUSTMENT[/bold yellow]"
            change_str = f"[yellow]~{m['quantity']}[/yellow]"

        table.add_row(
            m["timestamp"],
            type_badge,
            m["item_sku"],
            m["item_name"],
            change_str,
            str(m["previous_quantity"]),
            str(m["new_quantity"]),
            m["reason"]
        )

    console.print(table)

def handle_export_csv():
    filename = Prompt.ask("Export file path", default="inventory_export.csv")
    csv_data = db.export_items_csv()
    with open(filename, "w", encoding="utf-8") as f:
        f.write(csv_data)
    console.print(f"[bold green]✔ Successfully exported inventory to '{filename}'![/bold green]")

def handle_delete_item():
    sku = Prompt.ask("Enter item SKU or ID to delete").strip()
    item = None
    if sku.isdigit():
        item = db.get_item_by_id(int(sku))
    if not item:
        item = db.get_item_by_sku(sku)

    if not item:
        console.print(f"[red]Item '{sku}' not found![/red]")
        return

    if Confirm.ask(f"[bold red]Are you sure you want to permanently delete '[/bold red]{item.name}[bold red]' (SKU: {item.sku})?[/bold red]"):
        db.delete_item(item.id)
        console.print(f"[green]✔ Item '{item.name}' deleted successfully.[/green]")
    else:
        console.print("[yellow]Deletion cancelled.[/yellow]")

def main_menu():
    while True:
        print_header()
        display_summary()
        console.print("\n[bold cyan]Main Operations Menu:[/bold cyan]")
        console.print("  [bold]1.[/bold] 📋 View Full Inventory")
        console.print("  [bold]2.[/bold] 🔍 Search & Filter Products")
        console.print("  [bold]3.[/bold] ⚠️  View Low Stock & Out of Stock Alerts")
        console.print("  [bold]4.[/bold] 📥 Stock IN (Receive Goods / Restock)")
        console.print("  [bold]5.[/bold] 📤 Stock OUT (Sales Dispatch / Fulfill Order)")
        console.print("  [bold]6.[/bold] 🔧 Stock Adjustment (Physical Count Audit)")
        console.print("  [bold]7.[/bold] ➕ Add New Product")
        console.print("  [bold]8.[/bold] 🗑️  Delete Product")
        console.print("  [bold]9.[/bold] 📜 View Stock Movement History")
        console.print("  [bold]10.[/bold] 💾 Export Inventory to CSV")
        console.print("  [bold]0.[/bold] 🚪 Exit")

        choice = Prompt.ask("\nSelect an option", choices=["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10"], default="1")

        if choice == "1":
            print_header()
            list_inventory_table()
        elif choice == "2":
            handle_search()
        elif choice == "3":
            handle_low_stock_alerts()
        elif choice == "4":
            handle_stock_operation("IN")
        elif choice == "5":
            handle_stock_operation("OUT")
        elif choice == "6":
            handle_stock_operation("ADJUSTMENT")
        elif choice == "7":
            handle_add_item()
        elif choice == "8":
            handle_delete_item()
        elif choice == "9":
            handle_view_movements()
        elif choice == "10":
            handle_export_csv()
        elif choice == "0":
            console.print("\n[bold green]Thank you for using Inventory Stock Tracker! Goodbye.[/bold green]\n")
            sys.exit(0)

        Prompt.ask("\n[dim]Press Enter to return to main menu...[/dim]")

if __name__ == "__main__":
    main_menu()
