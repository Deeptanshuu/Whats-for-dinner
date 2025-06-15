# One container: the Flask API plus the built front end, on port 7860.

FROM node:20-slim AS web
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

FROM python:3.12-slim
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user PATH=/home/user/.local/bin:$PATH PYTHONUNBUFFERED=1
WORKDIR /home/user/app

COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt gunicorn==23.0.0

COPY --chown=user recsys recsys
COPY --chown=user server server
COPY --chown=user models models
COPY --chown=user data data
COPY --chown=user --from=web /web/dist web/dist

ENV WEB_DIST=/home/user/app/web/dist RECSYS_WARM=1
EXPOSE 7860
CMD ["gunicorn", "--bind", "0.0.0.0:7860", "--workers", "1", "--threads", "4", "--timeout", "120", "server.app:create_app()"]
