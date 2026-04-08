#!/bin/bash

echo "A iniciar servicos"

source .venv/bin/activate


echo "A iniciar redis"
redis-server &

sleep 2

echo "A iniciar celery"
celery -A config worker --loglevel=info &
sleep 2

echo "A iniciar servidor Django"
python manage.py runserver