#!/usr/bin/env bash
# Télécharge et installe le DSFR (Système de Design de l'État) auto-hébergé dans
# dashboard/dsfr/. Le dossier est volumineux et vendored -> hors git (.gitignore).
# À relancer après un clone frais, ou pour changer de version.
set -euo pipefail
VER="${1:-1.15.1}"
cd "$(dirname "$0")"
echo "Téléchargement DSFR $VER…"
curl -sL "https://registry.npmjs.org/@gouvfr/dsfr/-/dsfr-$VER.tgz" -o /tmp/dsfr.tgz
rm -rf /tmp/dsfr-x && mkdir -p /tmp/dsfr-x
tar xzf /tmp/dsfr.tgz -C /tmp/dsfr-x
rm -rf dashboard/dsfr && mkdir -p dashboard/dsfr
cp -R /tmp/dsfr-x/package/dist/* dashboard/dsfr/
cd dashboard/dsfr
# On ne garde que le nécessaire (css min + fonts + icônes + favicon + js min).
rm -rf component core analytics legacy artwork scheme dsfr example
find . -maxdepth 1 -name '*.css' ! -name 'dsfr.min.css' -delete
find utility -maxdepth 1 -name '*.css' ! -name 'utility.min.css' -delete
find utility -mindepth 1 -type d -exec rm -rf {} + 2>/dev/null || true
find . -maxdepth 1 -name '*.js' ! -name 'dsfr.module.min.js' ! -name 'dsfr.nomodule.min.js' -delete
find . -name '*.map' -delete
echo "DSFR $VER installé dans dashboard/dsfr ($(du -sh . | cut -f1))"
