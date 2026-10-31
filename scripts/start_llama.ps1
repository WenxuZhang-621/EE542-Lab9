param(
    [Parameter(Mandatory=$true)][string]$ServerPath,
    [Parameter(Mandatory=$true)][string]$ModelPath,
    [int]$GpuLayers = 0
)
$ErrorActionPreference = 'Stop'
if (-not (Test-Path -LiteralPath $ServerPath -PathType Leaf)) { throw 'Provide the built llama-server.exe path.' }
if (-not (Test-Path -LiteralPath $ModelPath -PathType Leaf)) { throw 'Provide your licensed Llama 3 Instruct GGUF model.' }
# Alias matches .env.example. CPU is the portable default; -GpuLayers needs a GPU build.
& $ServerPath -m $ModelPath --host 127.0.0.1 --port 8001 --ctx-size 4096 --alias llama-3-8b-instruct -ngl $GpuLayers
