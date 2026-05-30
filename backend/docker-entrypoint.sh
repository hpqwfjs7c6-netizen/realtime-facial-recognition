#!/bin/sh
set -e

# Le volume de données monté peut appartenir à root (volume nommé pré-existant
# ou bind-mount de l'hôte). On corrige sa propriété pour l'utilisateur non-root,
# puis on abandonne les privilèges root pour exécuter le serveur.
DATA_DIR="${DATA_DIR:-/app/data}"

if [ "$(id -u)" = "0" ]; then
    mkdir -p "$DATA_DIR"
    chown -R appuser:appuser "$DATA_DIR"
    exec gosu appuser "$@"
fi

# Déjà non-root (ex. USER imposé par l'orchestrateur) : exécution directe.
exec "$@"
