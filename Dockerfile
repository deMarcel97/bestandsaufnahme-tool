FROM python:3.11-slim

WORKDIR /srv/app
ENV PYTHONPATH=/srv/app

# Das Projekt ist ein Flat-Layout ohne __init__.py-Pakete (siehe README:
# lokal läuft es via `PYTHONPATH=.`), daher werden hier nur die
# Laufzeit-Abhängigkeiten aus pyproject.toml installiert statt das Projekt
# selbst als Package zu bauen.
COPY pyproject.toml ./
RUN pip install --no-cache-dir \
    "fastapi>=0.110.0" \
    "uvicorn[standard]>=0.28.0" \
    "jinja2>=3.1.3" \
    "pydantic>=2.6.3" \
    "pyyaml>=6.0.1" \
    "python-multipart>=0.0.9" \
    "python-docx>=1.1.0" \
    "authlib>=1.3.0" \
    "itsdangerous>=2.1.2" \
    "httpx>=0.27.0"

COPY app ./app
COPY schemas ./schemas
COPY rules ./rules
COPY bewertung ./bewertung

RUN mkdir -p /srv/app/data
VOLUME ["/srv/app/data"]

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips=*"]
