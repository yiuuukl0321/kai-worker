FROM python:3.11-slim
RUN pip install --no-cache-dir playwright requests
RUN python -m playwright install --with-deps chromium
WORKDIR /app
COPY worker.py .
CMD ["python", "-u", "worker.py"]
