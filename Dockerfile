FROM python:3.11-slim

WORKDIR /srv/app
ENV PYTHONPATH=/srv/app

# Das Projekt ist ein Flat-Layout ohne __init__.py-Pakete (siehe README:
# lokal läuft es via `PYTHONPATH=.`), daher werden hier nur die
# Laufzeit-Abhängigkeiten installiert statt das Projekt selbst als Package zu
# bauen. requirements.txt ist die gemeinsame Quelle für Container, Server-
# Installation (deploy/install.sh) und pyproject.toml.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY schemas ./schemas
COPY rules ./rules
COPY bewertung ./bewertung

RUN mkdir -p /srv/app/data
VOLUME ["/srv/app/data"]

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips=*"]
