# Stage 1: Build frontend
FROM node:18-alpine AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --legacy-peer-deps
COPY frontend/ .
RUN npm run build

# Stage 2: All-in-one runtime
FROM python:3.11-slim

WORKDIR /app

# Install system deps: nginx, supervisor, CJK fonts
RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx \
    supervisor \
    fonts-noto-cjk \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Python deps
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download pdf2zh/babeldoc fonts and models (avoid runtime download failures)
RUN python -c "import asyncio; from babeldoc.assets.assets import download_all_fonts_async; asyncio.run(download_all_fonts_async())" \
    && python -c "from pdf2zh.doclayout import DocLayoutModel; DocLayoutModel.load_available(); print('Model downloaded')"

# Copy backend
COPY backend/ /app/

# Copy built frontend
COPY --from=frontend-build /app/frontend/dist /usr/share/nginx/html

# Nginx config (rewrite upstream to localhost for all-in-one)
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
RUN sed -i 's|http://backend:8000|http://127.0.0.1:8000|g' /etc/nginx/conf.d/default.conf \
    && rm -f /etc/nginx/sites-enabled/default

# Create dirs
RUN mkdir -p /app/tmp /app/data /app/logs /var/log/supervisor

# Supervisor config
COPY <<'EOF' /etc/supervisor/conf.d/easypaper.conf
[supervisord]
nodaemon=true
logfile=/var/log/supervisor/supervisord.log

[program:backend]
command=uvicorn app.main:app --host 0.0.0.0 --port 8000
directory=/app
autostart=true
autorestart=true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0

[program:nginx]
command=nginx -g "daemon off;"
autostart=true
autorestart=true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0
EOF

EXPOSE 80 8000

CMD ["supervisord", "-c", "/etc/supervisor/supervisord.conf"]
