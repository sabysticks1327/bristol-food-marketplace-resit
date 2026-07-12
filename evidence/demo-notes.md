# Demo Notes

## Project Summary

This project is a Django and Docker implementation of the Bristol Regional Food Network marketplace. It turns the Term 1 business process into a working system covering customer shopping, producer fulfilment, inventory, test payment records, audit history, settlements, allergens, organic filtering, order history, reorder, security checks, and JSON API endpoints.

## Implemented Coverage

- 15 of 25 provided test cases implemented: TC-001 to TC-007, TC-009 to TC-012, TC-014, TC-015, TC-021, and TC-022.
- This is 60% of the provided test cases.
- Security/authentication checks are included through TC-022.
- Docker Compose runs the web app and PostgreSQL database.

## Demo Route

1. Show GitHub repository, README setup, Dockerfile, and docker-compose.yml.
2. Run the app with Docker:
   ```bash
   docker compose up --build
   ```
3. Open `http://localhost:8000/`.
4. Customer login:
   - Email: `robert.johnson@email.com`
   - Password: `StrongCustomerPass!2026`
5. Show marketplace browsing, category filter, search, organic filter, product detail, allergen warning, cart, checkout, order detail, order history, receipt download, and reorder.
6. Producer login:
   - Email: `jane.smith@bristolvalleyfarm.com`
   - Password: `StrongProducerPass!2026`
7. Show product management, stock/availability update, incoming orders, order status update, customer notification, weekly payment settlement, and CSV settlement report.
8. Show API endpoints:
   - `/api/`
   - `/api/products/`
   - `/api/products/?category=vegetables&organic=certified`
   - `/api/customer/orders/`
   - `/api/producer/orders/`
   - `/api/producer/settlements/`
9. Run tests:
   ```bash
   python manage.py test
   ```

## Term 1 Alignment

The Term 1 BPMN/i* work described a marketplace with customers, producers, a platform, payment service provider, courier service, and regulator/compliance concerns. This implementation focuses on the core platform flow:

- customer shops and submits order
- platform validates user role, stock, delivery date, and payment method
- stock is updated
- producer receives and fulfils order
- customer receives status updates
- payment records and settlement reports are auditable

External actors are simplified:

- PSP is represented by mock/test payment records.
- Courier integration is represented by delivery date/address workflow rather than a live courier API.
- Regulator/compliance reporting is represented by order history, status history, inventory update history, and settlement reports.

## Technical Explanation Points

- Django models persist users, producer/customer profiles, products, carts, orders, order items, payments, status history, inventory updates, alerts, and weekly settlements.
- Django authentication stores hashed passwords.
- Role checks prevent customers from producer-only pages and prevent producers from viewing another producer's orders/products.
- Checkout is limited to one producer, which keeps producer payment calculations simple and auditable.
- Payments use test/mock records only, following the test-case instruction not to use real financial data.
- JSON endpoints expose product/order/settlement data for API demonstration while preserving role-based access control.

## Known Limitations

- Multi-producer checkout is not implemented.
- Courier service integration is not implemented.
- Real payment provider integration is not implemented.
- Full regulator/admin commission dashboard is not implemented.
- Product reviews, recipes, surplus deals, recurring orders, and bulk orders are not implemented.

## Q&A Lines

- Why mock payments?
  - The test cases specifically say not to use real payment systems or actual financial data, so I used test payment records.
- How does this match Term 1?
  - Term 1 modelled the business process. This project implements the main customer order, stock, producer fulfilment, payment-recording, notification, and reporting flow.
- How is security handled?
  - Django authentication, password hashing, login protection, role-based access checks, ownership checks, and tested failure cases.
- What would be next?
  - Multi-producer checkout, richer API/DRF layer, courier integration, and admin commission reporting.
