FROM python:3.11-slim

# Dépendances système pour OpenCV / DeepFace + gosu (drop de privilèges)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 gosu \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV DATA_DIR=/app/data

# Utilisateur non-root. L'entrypoint (lancé en root) ajuste la propriété du
# volume de données monté — dont le propriétaire dépend de l'hôte — puis
# abandonne les privilèges via gosu pour exécuter le serveur en non-root.
RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /app/data \
    && chown -R appuser:appuser /app
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
# Neutralise d'éventuelles fins de ligne CRLF (checkout Windows) qui rendraient
# le shebang invalide ("exec: no such file or directory"), puis rend exécutable.
RUN sed -i 's/\r$//' /usr/local/bin/docker-entrypoint.sh \
    && chmod +x /usr/local/bin/docker-entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
