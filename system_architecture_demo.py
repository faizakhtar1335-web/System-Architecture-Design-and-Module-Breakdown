"""
Week 2 Task: System Architecture Design and Module Breakdown
Project: ShopEase - Modular E-commerce Platform

Purpose
-------
A self-contained, standard-library Python demonstration of the main business
modules described in the accompanying architecture report. This is an
educational prototype, not a production web service. It uses in-memory data
and simulates checkout; no real payment is processed.

Run:
    python system_architecture_demo.py

The prototype demonstrates:
- Product catalogue
- Shopping cart
- Order management
- Payment gateway adapter (simulated)
- Inventory management
- Notification adapter (simulated)
- A small end-to-end flow
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import uuid4


@dataclass
class Product:
    product_id: str
    name: str
    price: float
    stock: int


@dataclass
class CartItem:
    product_id: str
    quantity: int


@dataclass
class Order:
    order_id: str
    customer_email: str
    items: List[CartItem]
    total: float
    status: str
    created_at: str


class CatalogService:
    """Owns product lookup and catalogue-facing operations."""

    def __init__(self, products: Dict[str, Product]):
        self._products = products

    def list_products(self) -> List[Product]:
        return list(self._products.values())

    def get_product(self, product_id: str) -> Product:
        product = self._products.get(product_id)
        if product is None:
            raise ValueError(f"Product '{product_id}' was not found.")
        return product


class CartService:
    """Maintains a customer's selected items and calculates a cart total."""

    def __init__(self, catalog: CatalogService):
        self._catalog = catalog
        self._items: Dict[str, int] = {}

    def add_item(self, product_id: str, quantity: int = 1) -> None:
        if quantity <= 0:
            raise ValueError("Quantity must be greater than zero.")
        self._catalog.get_product(product_id)  # Validate product exists.
        self._items[product_id] = self._items.get(product_id, 0) + quantity

    def items(self) -> List[CartItem]:
        return [CartItem(pid, qty) for pid, qty in self._items.items()]

    def total(self) -> float:
        return sum(
            self._catalog.get_product(pid).price * qty
            for pid, qty in self._items.items()
        )

    def clear(self) -> None:
        self._items.clear()


class InventoryService:
    """Checks and reserves stock; a real system would use database transactions."""

    def __init__(self, catalog: CatalogService):
        self._catalog = catalog

    def check_available(self, items: List[CartItem]) -> None:
        for item in items:
            product = self._catalog.get_product(item.product_id)
            if item.quantity > product.stock:
                raise ValueError(
                    f"Insufficient stock for {product.name}: "
                    f"requested {item.quantity}, available {product.stock}."
                )

    def reserve(self, items: List[CartItem]) -> None:
        self.check_available(items)
        for item in items:
            self._catalog.get_product(item.product_id).stock -= item.quantity


class PaymentGatewayAdapter:
    """Simulates a payment provider; replace with a secure provider integration."""

    def charge(self, amount: float, order_id: str) -> str:
        if amount <= 0:
            raise ValueError("Payment amount must be greater than zero.")
        # No real charge occurs. Production code must use a provider SDK/API.
        return f"SIMULATED-{order_id}"


class NotificationService:
    """Simulates an email/order confirmation integration."""

    def send_order_confirmation(self, email: str, order: Order) -> None:
        print(f"[Notification] Confirmation queued for {email} "
              f"(order {order.order_id}, status: {order.status}).")


class OrderService:
    """Coordinates checkout and owns the order lifecycle."""

    def __init__(
        self,
        catalog: CatalogService,
        inventory: InventoryService,
        payment: PaymentGatewayAdapter,
        notifications: NotificationService,
    ):
        self._catalog = catalog
        self._inventory = inventory
        self._payment = payment
        self._notifications = notifications
        self._orders: Dict[str, Order] = {}

    def checkout(self, email: str, cart: CartService) -> Order:
        if "@" not in email or email.startswith("@") or email.endswith("@"):
            raise ValueError("Please provide a valid customer email address.")

        items = cart.items()
        if not items:
            raise ValueError("Cannot check out an empty cart.")

        total = cart.total()
        self._inventory.check_available(items)

        order_id = uuid4().hex[:10].upper()
        order = Order(
            order_id=order_id,
            customer_email=email,
            items=items,
            total=round(total, 2),
            status="PENDING_PAYMENT",
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        # In production, stock reservation, order persistence, and payment
        # require robust transaction/idempotency and failure-recovery handling.
        self._inventory.reserve(items)
        try:
            self._payment.charge(order.total, order.order_id)
            order.status = "CONFIRMED"
            self._orders[order.order_id] = order
            cart.clear()
            self._notifications.send_order_confirmation(email, order)
            return order
        except Exception:
            # Demo-level compensation. A production implementation needs
            # durable state and explicit stock-release/reconciliation logic.
            for item in items:
                self._catalog.get_product(item.product_id).stock += item.quantity
            raise

    def get_order(self, order_id: str) -> Optional[Order]:
        return self._orders.get(order_id)


def build_demo_application():
    """Composition root: creates modules and injects their dependencies."""
    products = {
        "P100": Product("P100", "Wireless Mouse", 799.00, 12),
        "P200": Product("P200", "USB-C Cable", 299.00, 25),
        "P300": Product("P300", "Laptop Stand", 1299.00, 7),
    }
    catalog = CatalogService(products)
    cart = CartService(catalog)
    inventory = InventoryService(catalog)
    payment = PaymentGatewayAdapter()
    notifications = NotificationService()
    orders = OrderService(catalog, inventory, payment, notifications)
    return catalog, cart, orders


def main():
    catalog, cart, orders = build_demo_application()

    print("=" * 56)
    print("ShopEase - System Architecture Demo")
    print("=" * 56)
    print("\nAvailable products:")
    for product in catalog.list_products():
        print(f"  {product.product_id}: {product.name} - "
              f"Rs. {product.price:.2f} (stock: {product.stock})")

    print("\nAdding two items to the cart...")
    cart.add_item("P100", 1)
    cart.add_item("P200", 2)
    print(f"Cart total: Rs. {cart.total():.2f}")

    email = input("\nEnter a customer email for the demo checkout: ").strip()
    try:
        order = orders.checkout(email, cart)
        print("\nOrder created successfully.")
        print(f"Order ID: {order.order_id}")
        print(f"Status:   {order.status}")
        print(f"Total:    Rs. {order.total:.2f}")
        print(f"Created:  {order.created_at}")
        print("\nRemaining stock:")
        for product in catalog.list_products():
            print(f"  {product.name}: {product.stock}")
    except ValueError as exc:
        print(f"\nCheckout could not be completed: {exc}")


if __name__ == "__main__":
    main()
