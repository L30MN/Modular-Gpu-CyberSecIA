#!/usr/bin/env bash
#
# Provisioning di un'istanza GPU Vast.ai per il progetto.
# Scopo: rendere l'istanza pronta con UN comando, mantenendo Ollama su localhost
# (accesso solo via tunnel SSH, nessuna porta pubblica esposta).
#
# USO A (consigliato): incolla questo contenuto nel campo "On-start Script" del
#   template Vast. Cosi' gira da solo a ogni avvio dell'istanza.
# USO B (manuale): nella terminale Vast dell'istanza esegui:
#   bash vast-provision.sh
#
# IMPORTANTE: qui NON impostiamo OLLAMA_HOST. Ollama resta in ascolto su
# localhost:11434, raggiungibile solo tramite il tunnel SSH dal tuo PC.
# Questa e' la scelta sicura: nessuna porta Ollama esposta su internet.

set -euo pipefail

# Modello da scaricare. Puoi sovrascriverlo con la variabile d'ambiente OLLAMA_MODEL.
MODEL="${OLLAMA_MODEL:-huihui_ai/qwen2.5-abliterate:32b}"

echo "[1/3] Attendo che il servizio Ollama risponda su localhost:11434..."
# Appena avviata, l'istanza puo' metterci qualche secondo ad alzare Ollama.
# Riprovo fino a ~60s prima di arrendermi.
for i in $(seq 1 30); do
  if curl -sf http://localhost:11434/ >/dev/null 2>&1; then
    echo "      Ollama e' attivo."
    break
  fi
  echo "      ...non ancora pronto ($i/30), riprovo tra 2s"
  sleep 2
done

echo "[2/3] Scarico il modello: $MODEL"
echo "      (prima volta: ~19 GB, puo' richiedere qualche minuto)"
# ollama pull e' idempotente: se il modello c'e' gia', non riscarica nulla.
ollama pull "$MODEL"

echo "[3/3] Verifica: modelli presenti sull'istanza"
ollama list

echo
echo "FATTO. L'istanza e' pronta."
echo "Dal tuo PC apri il tunnel:"
echo "  .\\open-tunnel.ps1 -HostIp <IP> -SshPort <PORTA>"
echo "Ollama resta su localhost: nessuna porta pubblica esposta."
