# 1. Basis-Image
FROM python:3.11-slim

# 2. Arbeitsverzeichnis im Container
WORKDIR /app

# 3. Systemabhängigkeiten (optional, hier minimal)
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# 4. Requirements zuerst kopieren (Layer-Cache)
COPY requirements.txt .

# 5. Python-Abhängigkeiten installieren
RUN pip install --no-cache-dir -r requirements.txt

# 6. Projektdateien kopieren
COPY . .

# 7. Port deklarieren
EXPOSE 5008

# 8. Startkommando
CMD ["python", "playingonsonos.py"]