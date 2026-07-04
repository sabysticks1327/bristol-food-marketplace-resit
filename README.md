# Bristol Regional Food Network Marketplace - Resit Project

This Django project currently implements **TC-001 to TC-005 only**.

## Implemented Test Cases

| Test Case | Feature | Status |
|---|---|---|
| TC-001 | Producer Registration | Implemented |
| TC-002 | Customer Registration | Implemented |
| TC-003 | Product Listing Creation | Implemented |
| TC-004 | Browse Products by Category | Implemented |
| TC-005 | Product Search | Implemented |

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
The tests also verify TC-003 to TC-005 product creation, producer-only access control, category browsing, visible product filtering, product detail display, search matching, and no-results handling.
