<#
.SYNOPSIS
  Apre il tunnel SSH verso l'istanza GPU su Vast.ai e inoltra Ollama sulla porta
  locale 11435.

.DESCRIPTION
  Mantiene l'Ollama remoto in ascolto solo su localhost (nessuna porta pubblica
  esposta): l'unico modo per raggiungerlo e' questo tunnel, autenticato dalla tua
  chiave SSH (servita dal Bitwarden SSH agent).

  Open WebUI resta configurato su http://host.docker.internal:11435 e NON va piu'
  toccato: a ogni nuova istanza cambia solo questo comando (nuovo IP / porta SSH),
  non la configurazione di Open WebUI.

.PARAMETER HostIp
  L'IP dell'istanza, dal pannello "SSH" dell'istanza su Vast.

.PARAMETER SshPort
  La porta SSH dell'istanza, dallo stesso pannello.

.PARAMETER BindAddress
  Interfaccia locale su cui aprire la porta 11435. Default 0.0.0.0, perche' il
  container Docker di Open WebUI possa raggiungere il tunnel via
  host.docker.internal.
  REQUISITO DI SICUREZZA: con 0.0.0.0 deve esistere la regola del Windows Firewall
  che BLOCCA l'inbound sulla porta 11435 per il profilo Public (gia' impostata nel
  progetto). Se preferisci non dipendere dal firewall usa -BindAddress 127.0.0.1,
  ma il container potrebbe non vedere il tunnel.

.EXAMPLE
  .\open-tunnel.ps1 -HostIp 123.45.67.89 -SshPort 41022
#>

param(
    [Parameter(Mandatory = $true)] [string] $HostIp,
    [Parameter(Mandatory = $true)] [int]    $SshPort,
    [string] $BindAddress = "0.0.0.0",
    [int]    $LocalPort   = 11435,
    [string] $RemoteUser  = "root"
)

# Formato richiesto da ssh -L :  <bind>:<porta_locale>:<host_remoto>:<porta_remota>
# Inoltra la porta locale verso il localhost:11434 DELL'ISTANZA (dove gira Ollama).
$forward = "{0}:{1}:localhost:11434" -f $BindAddress, $LocalPort

Write-Host "Tunnel SSH -> $RemoteUser@$HostIp porta $SshPort" -ForegroundColor Cyan
Write-Host "Inoltro locale ${BindAddress}:${LocalPort}  ->  remoto localhost:11434 (Ollama)" -ForegroundColor Cyan
Write-Host "Lascia questa finestra APERTA mentre lavori. Chiuderla chiude il tunnel." -ForegroundColor Yellow
Write-Host ""

# -N                      non esegue comandi remoti: tiene aperto solo il tunnel
# -L <forward>            inoltro di porta definito sopra
# ServerAliveInterval/Max ping periodici per non far cadere il tunnel se inattivo
# ExitOnForwardFailure    se la porta 11435 e' gia' occupata, esce subito con
#                         errore invece di aprire un tunnel "a meta'" che non inoltra
ssh -p $SshPort `
    -N `
    -L $forward `
    -o ServerAliveInterval=60 `
    -o ServerAliveCountMax=3 `
    -o ExitOnForwardFailure=yes `
    "$RemoteUser@$HostIp"