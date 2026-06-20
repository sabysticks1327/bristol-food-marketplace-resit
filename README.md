# Bristol Regional Food Network Marketplace - Resit Project

This Django project implements the core marketplace flows for **TC-001 to TC-010**.

## Implemented Test Cases

| Test Case | Feature | Status |
|---|---|---|
| TC-001 | Producer Registration | Implemented |
| TC-002 | Customer Registration | Implemented |
| TC-003 | Product Listing | Implemented |
| TC-004 | Browse Products by Category | Implemented |
| TC-005 | Product Search | Implemented |
| TC-006 | Shopping Cart | Implemented |
| TC-007 | Single Producer Checkout | Implemented |
| TC-008 | Multi-Producer Checkout | Implemented |
| TC-009 | Producer Order Dashboard | Implemented |
| TC-010 | Order Status Update | Implemented |

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

Second producer:

```text
Email: orders@hillsidedairy.example
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

The tests cover TC-001 through TC-010 and verify account roles, hashed passwords, product listing, category browsing, search, cart updates, single/multi-producer checkout, producer order visibility, and order status updates.
