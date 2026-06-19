# Merchant Platform API

## Setup

1. Create a Python virtual environment:

```bash
python -m venv venv
```

2. Activate it:

```bash
venv\Scripts\activate
```

3. Install dependencies:

```bash
python -m pip install django djangorestframework mysqlclient python-decouple
```

4. Create a `.env` file in the project root with:

```text
SECRET_KEY=your-secret-key
DEBUG=True
DB_NAME=merchant_db
DB_USER=root
DB_PASSWORD=your-password
DB_HOST=localhost
DB_PORT=3306
```

5. Run migrations:

```bash
python manage.py migrate
```

6. Run tests:

```bash
python manage.py test
```

7. Run the server:

```bash
python manage.py runserver
```

## API Endpoints

### Authentication

- `POST /api/auth/register/`
  - Body: `username`, `email`, `password`, `first_name`, `last_name`, `storeName`
  - Returns: `token`

- `POST /api/auth/login/`
  - Body: `username`, `password`
  - Returns: `token`

### Products

- `POST /api/products/`
- `GET /api/products/`
- `GET /api/products/:id/`
- `PATCH /api/products/:id/`
- `DELETE /api/products/:id/`

Product fields:
- `name`
- `description`
- `price`
- `category`
- `images`
- `isActive`
- `merchant`

### Variants

- `POST /api/products/:id/variants/`
- `GET /api/products/:id/variants/`
- `GET /api/variants/:id/`
- `PATCH /api/variants/:id/`
- `DELETE /api/variants/:id/`

Variant fields:
- `product`
- `color`
- `size`
- `stock`
- `priceOverride`

### Orders

- `POST /api/orders/`
- `GET /api/orders/`
- `GET /api/orders/:id/`

Order request body:
- `customerName`
- `customerPhone`
- `customerAddress`
- `items`: list of `{productVariant, quantity}`

### Dashboard

- `GET /api/dashboard/stats/`

Returns:
- `totalOrders`
- `totalRevenue`
- `totalProducts`
- `totalActiveProducts`
- `lowStockVariants`
- `topSellingProducts`
