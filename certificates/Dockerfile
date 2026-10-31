FROM python:3.12-slim-bookworm
RUN pip install --no-cache-dir certbot==5.9.0
COPY manager.py /manager.py
CMD ["python", "-u", "/manager.py"]
COPY tests.py /tests.py
RUN python /tests.py
