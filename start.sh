#!/bin/bash


nohup python manage.py celery beat &
nohup python manage.py celery worker &

cd /app
python manage.py runserver 0.0.0.0:8000
