#!/bin/sh
echo "Waiting for MySQL..."
while ! python -c "import MySQLdb; MySQLdb.connect(host='db',user='root',passwd='12345')" 2>/dev/null; do
  echo "MySQL not ready, retrying in 3s..."
  sleep 3
done
echo "MySQL is ready!"
python manage.py migrate
python -c "import nltk; nltk.download('punkt_tab', download_dir='/app/nltk_data')"
python manage.py runserver 0.0.0.0:8000