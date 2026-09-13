FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    xvfb x11vnc novnc websockify \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir playwright requests \
    && playwright install --with-deps chromium

WORKDIR /app
COPY worker.py .

CMD ["bash", "-c", "Xvfb :99 -screen 0 1280x800x24 & x11vnc -display :99 -forever -shared -nopw -quiet & websockify --web=/usr/share/novnc ${PORT:-8080} localhost:5900 & DISPLAY=:99 python worker.py"]
