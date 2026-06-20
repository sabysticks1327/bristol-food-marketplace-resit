# Bristol Regional Food Network Marketplace - Resit Project

This Django project currently implements **TC-001 only**.

## Implemented Test Cases

| Test Case | Feature | Status |
|---|---|---|
| TC-001 | Producer Registration | Implemented |

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

## Demo Producer Account

```text
Email: jane.smith@bristolvalleyfarm.com
Password: StrongProducerPass!2026
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

The tests verify TC-001 registration, producer role/profile creation, password hashing, duplicate email rejection, weak password rejection, login, and producer profile access.
