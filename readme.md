# The Midnight Artisan - Order & Inventory Management API

A Django REST API for managing inventory, orders, and automated invoice generation with asynchronous email delivery using Celery and Redis.

## Features

- 📦 **Inventory Management** - Create and manage product inventory with stock tracking
- 🛒 **Order Processing** - Create orders with automatic stock deduction
- 📧 **Automated Invoicing** - Generate and send text-based invoices via email
- ⚡ **Async Task Queue** - Non-blocking invoice delivery using Celery and Redis
- 🔄 **Retry Logic** - Automatic retry on SMTP failures (up to 3 attempts)
- 🔐 **UUID-based IDs** - Secure, non-sequential identifiers for all resources

## System Design

![System Design](docs/system-design.png)

## Tech Stack

- **Backend:** Django 5.x, Django REST Framework
- **Database:** PostgreSQL/SQLite (configurable)
- **Task Queue:** Celery 5.x
- **Message Broker:** Redis
- **Email:** SMTP (Gmail, Mailtrap, etc.)

## Prerequisites

- Python 3.10+
- Redis
- pip

## Installation

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/the-midnight-artisan.git
cd the-midnight-artisan
```

### 2. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Install Redis

**macOS:**
```bash
brew install redis
brew services start redis
```

**Ubuntu/Debian:**
```bash
sudo apt-get install redis-server
sudo systemctl start redis
```

**Windows:**
Download from [Redis Windows](https://github.com/microsoftarchive/redis/releases)

### 5. Environment Variables

Create a `.env` file in the project root:
```env
# Django
SECRET_KEY=your-secret-key-here
DEBUG=True

# Email Configuration
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-16-char-app-password

# Optional: Database (if using PostgreSQL)
DATABASE_URL=postgresql://user:password@localhost:5432/dbname
```

**Gmail App Password Setup:**
1. Enable 2-Step Verification in your Google Account
2. Go to [App Passwords](https://myaccount.google.com/apppasswords)
3. Generate password for "Mail" → "Other (Custom name)"
4. Copy the 16-character password (remove spaces) to `.env`

### 6. Database Setup
```bash
python manage.py makemigrations
python manage.py migrate
```

### 7. Create Superuser (Optional)
```bash
python manage.py createsuperuser
```

## Running the Application

You need **3 terminals** for full async functionality:

### Terminal 1: Redis
```bash
redis-server
```

### Terminal 2: Celery Worker
```bash
celery -A your_project_name worker --loglevel=info
```

### Terminal 3: Django Server
```bash
python manage.py runserver
```

**Alternative: Development Mode (No Redis/Celery)**

For simpler development, enable synchronous mode in `settings.py`:
```python
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
```

Then just run:
```bash
python manage.py runserver
```

Invoices will be sent synchronously (slower but simpler).

## API Endpoints

### Inventory

#### Create Product
```http
POST /api/v1/products/
Content-Type: application/json

{
  "product_name": "Laptop",
  "product_price": 999.99,
  "stock_quantity": 50
}
```

**Response:**
```json
{
  "message": "Product created successfully",
  "data": {
    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "product_name": "Laptop",
    "product_price": "999.99",
    "stock_quantity": 50,
    "created_at": "2026-02-11T14:30:00Z",
    "updated_at": "2026-02-11T14:30:00Z"
  }
}
```

### Orders

#### Create Order
```http
POST /api/v1/orders/
Content-Type: application/json

{
  "customer_name": "John Doe",
  "customer_email": "john@example.com",
  "items": [
    {
      "product_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "quantity": 2
    }
  ]
}
```

**Response:**
```json
{
  "message": "Order created successfully. Invoice will be sent shortly.",
  "data": {
    "id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
    "customer_name": "John Doe",
    "customer_email": "john@example.com",
    "created_at": "2026-02-11T14:35:00Z",
    "updated_at": "2026-02-11T14:35:00Z",
    "is_invoice_sent": false,
    "items": [
      {
        "id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
        "product_name": "Laptop",
        "quantity": 2,
        "price_at_purchase": "999.99",
        "subtotal": "1999.98"
      }
    ],
    "total_amount": "1999.98"
  },
  "task_id": "d4e5f6a7-b8c9-0123-def1-234567890123",
  "invoice_status": "queued"
}
```

#### List Orders
```http
GET /api/v1/orders/
```

#### Get Order Details
```http
GET /api/v1/orders/{order_id}/
```

## Invoice Format

Invoices are sent as plain text emails:
```
============================================================
INVOICE
============================================================

Order ID: b2c3d4e5-f6a7-8901-bcde-f12345678901
Date: February 11, 2026 02:35 PM

------------------------------------------------------------
CUSTOMER INFORMATION
------------------------------------------------------------
Name: John Doe
Email: john@example.com

------------------------------------------------------------
ORDER ITEMS
------------------------------------------------------------
Item                           Qty   Price      Subtotal  
------------------------------------------------------------
Laptop                         2     $999.99    $1999.98  

------------------------------------------------------------
TOTAL                                          $  1999.98
============================================================

Thank you for your order!
```

## Management Commands

### Retry Failed Invoices

If invoices fail to send (SMTP issues, Redis down, etc.), retry them:
```bash
python manage.py retry_failed_invoices --limit=100
```

This queues invoice tasks for all orders where `is_invoice_sent=False`.

## Project Structure
```
the-midnight-artisan/
├── manage.py
├── requirements.txt
├── .env
├── README.md
├── your_project/
│   ├── __init__.py          # Celery app import
│   ├── settings.py          # Django settings
│   ├── celery.py            # Celery configuration
│   ├── urls.py              # Main URL routing
│   └── wsgi.py
├── core/                     # Main app
│   ├── models.py            # Inventory, Order, OrderItem
│   ├── serializers.py       # DRF serializers
│   ├── views.py             # API views
│   ├── services.py          # Business logic (InvoiceService)
│   ├── tasks.py             # Celery tasks
│   ├── urls.py              # App URL routing
│   └── management/
│       └── commands/
│           └── retry_failed_invoices.py
└── static/
```

## Configuration

### Celery Settings (`settings.py`)
```python
# Redis as message broker and result backend
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'

# Serialization
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'

# Task configuration
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes
CELERY_TASK_ACKS_LATE = True  # Acknowledge after completion
CELERY_TASK_REJECT_ON_WORKER_LOST = True  # Re-queue if worker crashes

# Connection settings
CELERY_BROKER_CONNECTION_RETRY = True
CELERY_BROKER_CONNECTION_MAX_RETRIES = 10
```

### Email Settings
```python
# Development (console output)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Production (SMTP)
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = config('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = config('EMAIL_HOST_USER')
EMAIL_TIMEOUT = 10
```

## Error Handling

### Task Retry Logic

Celery tasks automatically retry on SMTP failures:
- **Max retries:** 3
- **Backoff:** Exponential (2s, 4s, 8s)
- **Jitter:** Random delay to prevent thundering herd
- **Auto-retry on:** `SMTPException`, `ConnectionError`, network errors

### Graceful Degradation

If Redis is unavailable:
- Order is still created
- API returns warning: `"invoice_status": "failed"`
- Use `retry_failed_invoices` command when Redis is back

## Monitoring

### Check Redis Queue
```bash
redis-cli
> LLEN celery  # Number of pending tasks
> LRANGE celery 0 -1  # View tasks
```

### Check Celery Workers
```bash
celery -A your_project inspect active  # Active tasks
celery -A your_project inspect stats   # Worker statistics
```

### Flower (Web-based Monitoring)
```bash
pip install flower
celery -A your_project flower
# Visit http://localhost:5555
```

## Testing

### Run Tests
```bash
python manage.py test
```

### Manual Testing
```bash
# Create a product
curl -X POST http://localhost:8000/api/v1/products/ \
  -H "Content-Type: application/json" \
  -d '{"product_name": "Test Product", "product_price": 10.00, "stock_quantity": 100}'

# Create an order (replace PRODUCT_ID)
curl -X POST http://localhost:8000/api/v1/orders/ \
  -H "Content-Type: application/json" \
  -d '{
    "customer_name": "Test User",
    "customer_email": "test@example.com",
    "items": [{"product_id": "PRODUCT_ID", "quantity": 1}]
  }'
```

## Deployment

### Production Checklist

- [ ] Set `DEBUG=False` in settings
- [ ] Configure production database (PostgreSQL recommended)
- [ ] Use environment variables for secrets
- [ ] Set up proper SMTP server
- [ ] Use managed Redis (AWS ElastiCache, Redis Cloud, etc.)
- [ ] Run Celery with supervisor/systemd
- [ ] Use Gunicorn/uWSGI for Django
- [ ] Set up Nginx as reverse proxy
- [ ] Configure HTTPS/SSL
- [ ] Set up logging and monitoring
- [ ] Configure CORS if needed

### Example Production Stack
```
Users → Nginx (HTTPS) → Gunicorn (Django) → PostgreSQL
                             ↓
                         Redis ← Celery Workers
```

## Troubleshooting

### Emails not sending
```bash
# Check Redis
redis-cli ping  # Should return PONG

# Check Celery worker
ps aux | grep celery | grep -v grep

# Check email settings
python manage.py shell
>>> from django.conf import settings
>>> print(settings.EMAIL_HOST_USER)
>>> print(settings.EMAIL_BACKEND)
```

### Tasks stuck in queue
```bash
# Check Redis queue
redis-cli LLEN celery

# Purge all tasks (careful!)
celery -A your_project purge

# Restart worker
pkill -f "celery worker"
celery -A your_project worker --loglevel=info
```

### Connection errors
```bash
# Check if Redis is accessible
redis-cli -h localhost -p 6379 ping

# Check Celery can connect to Redis
celery -A your_project inspect ping
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

<!-- ## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details. -->

## Contact

Ifeoluwase - [@X (f.k.a Twitter)](https://twitter.com/tee__high) - taiwoifeoluwa023@example.com

Project Link: [https://github.com/TeeHigh/the-midnight-artisan](https://github.com/TeeHigh/the-midnight-artisan)

## Acknowledgments

- Django REST Framework
- Celery
- Redis
- Python community

---

**Built with ❤️ by [Ifeoluwase]**