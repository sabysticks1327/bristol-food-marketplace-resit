# Bristol Regional Food Network Marketplace - Resit Project

This Django project currently implements **TC-001 to TC-007, TC-009 to TC-011, TC-015, and TC-022 only**.

## Implemented Test Cases

| Test Case | Feature | Status |
|---|---|---|
| TC-001 | Producer Registration | Implemented |
| TC-002 | Customer Registration | Implemented |
| TC-003 | Product Listing Creation | Implemented |
| TC-004 | Browse Products by Category | Implemented |
| TC-005 | Product Search | Implemented |
| TC-006 | Shopping Cart | Implemented |
| TC-007 | Single-Producer Checkout | Implemented |
| TC-009 | Producer Incoming Orders | Implemented |
| TC-010 | Order Status Updates | Implemented |
| TC-011 | Inventory Updates | Implemented |
| TC-015 | Allergen Warnings | Implemented |
| TC-022 | Secure Authentication and Authorisation | Implemented |

## TC-001 Coverage

- Producer registration page.
- Business name, contact name, email, phone, business address, postcode, and password fields.
- Django password validation.
- User account creation through Django authentication.
- Secure password hashing.
- Producer role assignment through a `Producer` group and `ProducerProfile.role`.
- Saved producer profile.
- Login with registered credentials.
- Authenticated producer profile page.

## TC-002 Coverage

- Customer registration page.
- Full name, email, phone, delivery address, postcode, terms, and password fields.
- Django password validation.
- User account creation through Django authentication.
- Secure password hashing.
- Customer role assignment through a `Customer` group and `CustomerProfile.role`.
- Saved customer profile and delivery address.
- Login with registered credentials.
- Authenticated customer account page.

## TC-003 Coverage

- Authenticated producer product listing page.
- Product fields for name, category, description, price, unit, availability, stock quantity, allergen information, and harvest date.
- Product records linked to the logged-in producer profile.
- Producer dashboard table listing the producer's own products.
- Product edit route limited to the owning producer.
- Customer accounts blocked from producer-only product creation.

## TC-004 Coverage

- Public marketplace browse page.
- Category model and category filter links.
- Customer-visible products filtered by availability and stock quantity.
- Product cards showing producer, category, price, unit, availability, and stock quantity.
- Product detail page for visible products.

## TC-005 Coverage

- Marketplace search by product name.
- Marketplace search by product description.
- Marketplace search by producer business name.
- Combined category and search parameters.
- No-results message when no visible product matches the search.

## TC-006 Coverage

- Logged-in customers can add visible products to a persistent cart.
- Cart page shows product, producer, unit price, quantity, line total, and cart total.
- Cart navigation displays the current item count.
- Customers can update item quantities.
- Customers can remove items from the cart.
- Producer information is shown for multi-vendor awareness.
- Producer accounts are blocked from customer cart access.

## TC-007 Coverage

- Checkout is available when the cart contains products from one producer.
- Checkout is blocked when the cart contains products from multiple producers.
- Delivery address and postcode are pre-filled from the customer profile.
- Delivery date validation enforces at least 48 hours lead time.
- Order records are created with `Pending` status.
- Order items preserve purchased product, quantity, and price details.
- Test sandbox payment records are stored.
- 5% network commission and 95% producer payment are calculated and recorded.
- Customer and producer can view the confirmed order.
- Other producers are blocked from viewing orders they do not own.

## TC-009 Coverage

- Producer order management page.
- Incoming orders are sorted by delivery date.
- Order rows show order number, customer, order date, delivery date, status, item summary, total value, and lead time.
- Order detail page shows customer name, phone, email, delivery address, itemised products, and special instructions.
- Producers can filter orders by status.
- Producers cannot access another producer's orders.

## TC-010 Coverage

- Producers can update their own order status.
- Status progression is enforced: `Pending` -> `Confirmed` -> `Ready for Delivery` -> `Delivered`.
- Status skipping is rejected.
- Status history records timestamp, note, status, and producer.
- Customer notifications are created for status updates.
- Customer account and order detail views show updated status.

## TC-011 Coverage

- Producers can update stock quantities and availability from the product edit page.
- Stock validation rejects negative values.
- Availability changes immediately affect public product visibility.
- Inventory update history records previous and new stock/availability.
- Low-stock alerts are created and shown to producers.
- Producers can only edit their own products.

## TC-015 Coverage

- Allergen information is required when producers list or edit products.
- Product cards and product detail pages show clear allergen warnings before cart actions.
- Products with allergens use `Contains:` warning language.
- Products without listed allergens show `No common allergens`.
- Product search includes allergen information.
- Marketplace allergen filters support `Contains allergens` and `No common allergens`.
- Customers must acknowledge allergen information before adding products to cart.

## TC-022 Coverage

- Password validation rejects weak passwords.
- Passwords are stored as Django password hashes, not plain text.
- Failed login attempts are recorded.
- Basic login rate limiting blocks too many recent failures.
- Correct login creates an authenticated session.
- Logout terminates the session and protected pages require re-login.
- Role-based access control blocks customers from producer-only features.
- Product ownership checks prevent one producer editing another producer's product.
- Order authorisation prevents unrelated producers viewing another producer's order.
- Search uses Django ORM filtering and does not expose unavailable products through injection-style input.

## Local Setup

```bash
python manage.py migrate
python manage.py seed_demo_data
python manage.py runserver 127.0.0.1:8000 --noreload
```

Open:

```text
http://127.0.0.1:8000/
```

## Demo Accounts

Producer:

```text
Email: jane.smith@bristolvalleyfarm.com
Password: StrongProducerPass!2026
```

Customer:

```text
Email: robert.johnson@email.com
Password: StrongCustomerPass!2026
```

## Docker

```bash
docker compose up --build
```

The Docker setup runs:

- `web`: Django + Gunicorn
- `db`: PostgreSQL

## Tests

```bash
python manage.py test
```

The tests verify TC-001 and TC-002 registration, role/profile creation, password hashing, duplicate/invalid registration handling, login, and profile/account access.
The tests also verify TC-003 to TC-007, TC-009 to TC-011, TC-015, and TC-022 product creation, producer-only access control, category browsing, visible product filtering, product detail display, search matching, cart updates, single-producer checkout, payment record creation, commission calculation, incoming order management, order status history, customer notifications, inventory update history, low-stock alerts, allergen warnings, allergen acknowledgement, login failure logging, rate limiting, logout, and protected-page checks.
