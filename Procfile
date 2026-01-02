web: gunicorn nowa_backend.wsgi --bind 0.0.0.0:$PORT
worker: celery -A nowa_backend worker --loglevel=info --concurrency=4