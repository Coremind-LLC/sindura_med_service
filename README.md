# Sindura Med Service

Sindura эмнэлгийн цаг захиалгын backend API. Django 6 + Django REST Framework, PostgreSQL, Redis (cache, Celery broker), Celery (захиалгын хугацаа дуусахыг шалгах), QPay (төлбөр), CallPro (SMS).

## Бүтэц

| Хавтас | Агуулга |
| --- | --- |
| `config/` | Django settings, URL, Celery тохиргоо |
| `apps/auth` | Нэвтрэх, OTP, нууц үг сэргээх |
| `apps/user`, `apps/doctor` | Хэрэглэгч, эмч |
| `apps/examination_type`, `apps/examination_pack`, `apps/examination` | Үзлэгийн төрөл, хуваарь, цаг |
| `apps/order`, `apps/invoice`, `apps/payment` | Захиалга, нэхэмжлэх, төлбөр |
| `apps/third_party/qpay`, `apps/third_party/call_pro` | Гадаад үйлчилгээний client |
| `apps/activity_log` | Үйлдлийн түүх |
| `helpers/` | Туслах функцууд, тестийн factory |

## Орчны хувьсагч (`.env`)

Repo-ийн root-д `.env` файл үүсгэнэ (git-д орохгүй):

```
DEBUG=True
SECRET_KEY=...
ALLOWED_HOSTS=localhost,127.0.0.1
DB_NAME=... DB_USER=... DB_PASSWORD=... DB_HOST=... DB_PORT=5432
REDIS_HOST=... REDIS_PORT=6379
CALL_PRO_URL=... CALL_PRO_KEY=... CALL_PRO_FROM=...
QPAY_HOST=... QPAY_USER=... QPAY_PASSWORD=... QPAY_INVOICE_CODE=...
```

Production-д нэмэлтээр:

| Хувьсагч | Анхдагч | Тайлбар |
| --- | --- | --- |
| `DEBUG` | `False` | Production-д `False`. `True` үед бүх CORS origin зөвшөөрөгдөнө (локал хөгжүүлэлт). |
| `CORS_ALLOWED_ORIGINS` | `https://sindura-med-admin.monos.mn,https://sindura-med.monos.mn` | Browser-оос API дуудах эрхтэй frontend домэйнууд |
| `ALLOWED_HOSTS` | `sindura-med-api.monos.mn,localhost,127.0.0.1` | API-ийн домэйн |
| `API_HOST` | `https://sindura-med-api.monos.mn` | QPay callback (`/payments/get_payment/`) энэ хаяг руу ирнэ |
| `NUM_PROXIES` | `1` | API-ийн өмнөх proxy-н тоо (nginx). Rate limit клиентийн IP-г `X-Forwarded-For`-оос авна |
| `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE` | `not DEBUG` | Cookie-г зөвхөн HTTPS-ээр дамжуулах |
| `SECURE_SSL_REDIRECT` | `False` | HTTPS-ийг reverse proxy-гүйгээр шууд Django хүлээн авдаг бол `True` |
| `SECURE_HSTS_SECONDS` | `0` | HTTPS бүрэн ажилладаг болсны дараа `31536000` болгоно |
| `AUTH_THROTTLE_RATE` | `60/minute` | `/auth/` (login, OTP) endpoint-д нэг IP-ээс ирэх хүсэлтийн хязгаар |
| `ORDER_LOOKUP_THROTTLE_RATE` | `60/minute` | Нэвтрээгүй "Миний захиалга" хайлтын (`GET /orders/?search=`) хязгаар |
| `SERVE_MEDIA` | `True` | `/media/`-г Django өөрөө serve хийнэ. Nginx serve хийдэг болсон бол `False` |

Nginx нь клиентийн IP-г дамжуулах ёстой: `proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;`

## Локал ажиллуулах

Docker-оор (web, celery, celery-beat, postgres, redis):

```
docker compose up --build
docker compose exec web python manage.py migrate
```

Docker-гүй:

```
python3 -m venv venv
venv/bin/pip install -r requirements.txt
venv/bin/python manage.py migrate
venv/bin/python manage.py runserver
venv/bin/celery -A config worker -l info
venv/bin/celery -A config beat -l info
```

API баримт: `/swagger/`, `/redoc/`.

## Тест

Тестүүд PostgreSQL (ArrayField ашигладаг) дээр ажиллана, cache нь санах ойд, гадаад HTTP дуудлага бүгд mock хийгдсэн:

```
venv/bin/python manage.py test --settings=config.settings_test
```

`DB_*` хувьсагч тестийн өгөгдлийн сан үүсгэх эрхтэй сервер рүү заасан байх ёстой (`test_<DB_NAME>` нэртэй сан үүсгээд устгана).

## Deploy

`prod` branch руу push хийхэд `.github/workflows/deploy-prod.yml` image-ийг build хийж `ghcr.io/coremind-llc/sindura_med_service:prod` болгон GHCR руу push хийнэ. Сервер дээрх WUD (What's Up Docker) шинэ image-ийг татаж контейнерийг дахин асаана. Контейнер асахдаа `migrate`, `collectstatic` ажиллуулаад gunicorn-оор serve хийнэ (static файлыг whitenoise).
