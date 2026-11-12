param(
  [Parameter(Mandatory = $true)][string]$Entrada,
  [Parameter(Mandatory = $true)][string]$Saida,
  [string]$Formato = 'feed',
  [string]$Raiz = '',
  [int]$IntervaloMs = 50
)

$ErrorActionPreference = 'Stop'
$imagemDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoDir = Resolve-Path (Join-Path $imagemDir '..\..')
$provaDir = Join-Path $imagemDir '.sandbox\prova'
New-Item -ItemType Directory -Force $provaDir | Out-Null
$logRender = Join-Path $provaDir 'render.log'
$errRender = Join-Path $provaDir 'render.err.log'
$csvConexoes = Join-Path $provaDir 'conexoes.csv'
$csvProcessos = Join-Path $provaDir 'processos.csv'
$jsonResumo = Join-Path $provaDir 'resumo.json'
foreach ($f in @($logRender, $errRender, $csvConexoes, $csvProcessos, $jsonResumo)) { if (Test-Path $f) { Remove-Item $f -Force } }

$python = (Get-Command python).Source
$render = Join-Path $imagemDir 'render.py'
$argumentos = @("`"$render`"", "`"$Entrada`"", "`"$Saida`"", '--formato', $Formato)
if ($Raiz) { $argumentos += @('--raiz', "`"$Raiz`"") }
$proc = Start-Process -FilePath $python -ArgumentList $argumentos `
  -WorkingDirectory $repoDir -RedirectStandardOutput $logRender -RedirectStandardError $errRender -PassThru -WindowStyle Hidden
$null = $proc.Handle
$raiz = $proc.Id

$vistos = @{}
$conexoes = @{}
$amostras = 0
$inicio = Get-Date

function Get-Arvore([int]$raizPid) {
  $todos = Get-CimInstance Win32_Process -Property ProcessId, ParentProcessId, Name, CommandLine, CreationDate
  $filhos = @{}
  foreach ($p in $todos) {
    $pp = [int]$p.ParentProcessId
    if (-not $filhos.ContainsKey($pp)) { $filhos[$pp] = New-Object System.Collections.ArrayList }
    [void]$filhos[$pp].Add($p)
  }
  $porPid = @{}
  foreach ($p in $todos) { $porPid[[int]$p.ProcessId] = $p }
  $arvore = @{}
  $fila = New-Object System.Collections.Queue
  if ($porPid.ContainsKey($raizPid)) { $arvore[$raizPid] = $porPid[$raizPid] }
  $fila.Enqueue($raizPid)
  while ($fila.Count -gt 0) {
    $atual = $fila.Dequeue()
    if ($filhos.ContainsKey($atual)) {
      foreach ($c in $filhos[$atual]) {
        $cpid = [int]$c.ProcessId
        if ($cpid -ne $atual -and -not $arvore.ContainsKey($cpid)) {
          if ($c.CreationDate -ge $porPid[$atual].CreationDate) {
            $arvore[$cpid] = $c
            $fila.Enqueue($cpid)
          }
        }
      }
    }
  }
  return $arvore
}

while (-not $proc.HasExited) {
  $amostras++
  $arvore = Get-Arvore $raiz
  foreach ($k in $arvore.Keys) {
    if (-not $vistos.ContainsKey($k)) {
      $p = $arvore[$k]
      $vistos[$k] = [pscustomobject]@{ PID = $k; PPID = [int]$p.ParentProcessId; Nome = $p.Name; Linha = $p.CommandLine }
    }
  }
  $pids = @($arvore.Keys)
  if ($pids.Count -gt 0) {
    $tcp = Get-NetTCPConnection -ErrorAction SilentlyContinue | Where-Object { $pids -contains [int]$_.OwningProcess }
    foreach ($t in $tcp) {
      $chave = "tcp|$($t.OwningProcess)|$($t.LocalAddress):$($t.LocalPort)|$($t.RemoteAddress):$($t.RemotePort)|$($t.State)"
      if (-not $conexoes.ContainsKey($chave)) {
        $conexoes[$chave] = [pscustomobject]@{
          Protocolo = 'TCP'; PID = [int]$t.OwningProcess; Processo = $vistos[[int]$t.OwningProcess].Nome
          Local = "$($t.LocalAddress):$($t.LocalPort)"; Remoto = "$($t.RemoteAddress):$($t.RemotePort)"
          RemotoIP = "$($t.RemoteAddress)"; Estado = "$($t.State)"; VistoEm = ((Get-Date) - $inicio).TotalSeconds.ToString('0.0')
        }
      }
    }
    $udp = Get-NetUDPEndpoint -ErrorAction SilentlyContinue | Where-Object { $pids -contains [int]$_.OwningProcess }
    foreach ($u in $udp) {
      $chave = "udp|$($u.OwningProcess)|$($u.LocalAddress):$($u.LocalPort)"
      if (-not $conexoes.ContainsKey($chave)) {
        $conexoes[$chave] = [pscustomobject]@{
          Protocolo = 'UDP'; PID = [int]$u.OwningProcess; Processo = $vistos[[int]$u.OwningProcess].Nome
          Local = "$($u.LocalAddress):$($u.LocalPort)"; Remoto = '(udp sem par remoto)'; RemotoIP = ''
          Estado = 'Bound'; VistoEm = ((Get-Date) - $inicio).TotalSeconds.ToString('0.0')
        }
      }
    }
  }
  Start-Sleep -Milliseconds $IntervaloMs
}
$proc.WaitForExit()
$duracao = ((Get-Date) - $inicio).TotalSeconds

function Test-Loopback([string]$ip) {
  if ([string]::IsNullOrEmpty($ip)) { return $true }
  if ($ip -eq '::1' -or $ip -eq '0.0.0.0' -or $ip -eq '::') { return $true }
  if ($ip.StartsWith('127.') -or $ip.StartsWith('::ffff:127.')) { return $true }
  return $false
}

$lista = @($conexoes.Values | Sort-Object { [double]$_.VistoEm })
$lista | Export-Csv -NoTypeInformation -Encoding UTF8 $csvConexoes
@($vistos.Values | Sort-Object PID) | Export-Csv -NoTypeInformation -Encoding UTF8 $csvProcessos
$tcpLista = @($lista | Where-Object { $_.Protocolo -eq 'TCP' })
$externos = @($tcpLista | Where-Object { -not (Test-Loopback $_.RemotoIP) })
$udpExternos = @($lista | Where-Object { $_.Protocolo -eq 'UDP' -and -not (Test-Loopback (($_.Local -split ':')[0])) })
$remotos = @($tcpLista | ForEach-Object { $_.RemotoIP } | Sort-Object -Unique)
$escuta = @($tcpLista | Where-Object { $_.Estado -eq 'Listen' } | ForEach-Object { "$($_.Processo) $($_.Local)" } | Sort-Object -Unique)
$sink = @($tcpLista | Where-Object { $_.Remoto -match ':9$' -and $_.RemotoIP.StartsWith('127.') })
$esperados = @('python.exe', 'python3.11.exe', 'chrome.exe', 'chrome-headless-shell.exe', 'msedge.exe', 'conhost.exe', 'taskkill.exe')
$inesperados = @($vistos.Values | Where-Object { $esperados -notcontains $_.Nome.ToLower() } | ForEach-Object { "$($_.Nome) pid=$($_.PID) pai=$($_.PPID): $($_.Linha)" })
$saidaRender = if (Test-Path $logRender) { Get-Content $logRender -Encoding UTF8 } else { @() }
$redeOk = [bool]($saidaRender | Where-Object { $_ -match '^\[OK\] nenhum pedido para fora' })
$pecasOk = @($saidaRender | Where-Object { $_ -match '^\[OK\] peca ' }).Count
$pecasFalhas = @($saidaRender | Where-Object { $_ -match '^\[FALHOU\] peca ' }).Count
$chromes = @($vistos.Values | Where-Object { $_.Nome -match 'chrome|msedge' -and $_.Linha -match '--type=' -eq $false })
$flags = @($chromes | ForEach-Object {
  [pscustomobject]@{
    PID = $_.PID
    ProxySink = [bool]($_.Linha -match '--proxy-server=http://127\.0\.0\.1:9')
    HostResolverRules = [bool]($_.Linha -match '--host-resolver-rules=')
    NoSandbox = [bool]($_.Linha -match '--no-sandbox')
    Headless = [bool]($_.Linha -match '--headless')
    DevToolsPortaAleatoria = [bool]($_.Linha -match '--remote-debugging-port=0')
    PerfilNoSandbox = [bool]($_.Linha -match [regex]::Escape((Join-Path $imagemDir '.sandbox')))
  }
})

$resumo = [ordered]@{
  raiz_pid = $raiz
  codigo_saida_render = $proc.ExitCode
  duracao_s = [math]::Round($duracao, 1)
  amostras = $amostras
  intervalo_ms = $IntervaloMs
  pecas_ok = $pecasOk
  pecas_com_falha = $pecasFalhas
  processos_na_arvore = $vistos.Count
  processos_por_nome = @($vistos.Values | Group-Object Nome | ForEach-Object { "$($_.Name) x$($_.Count)" })
  portas_em_escuta = $escuta
  conexoes_tcp_unicas = $tcpLista.Count
  enderecos_remotos_tcp = $remotos
  conexoes_tcp_nao_loopback = $externos.Count
  udp_em_endereco_nao_loopback = $udpExternos.Count
  tentativas_no_sumidouro_127_0_0_1_9 = $sink.Count
  render_sem_pedido_externo = $redeOk
  processos_fora_do_esperado = $inesperados
  chrome_navegador_flags = $flags
  veredito = if ($externos.Count -eq 0 -and $udpExternos.Count -eq 0 -and $redeOk -and $proc.ExitCode -eq 0) { 'SO_LOOPBACK' } else { 'VERIFICAR' }
}
$resumo | ConvertTo-Json -Depth 5 | Set-Content -Encoding UTF8 $jsonResumo
$resumo | ConvertTo-Json -Depth 5
if ($externos.Count -gt 0) { "Conexoes nao-loopback:"; $externos | Format-Table -AutoSize | Out-String }
"Arquivos: $provaDir"
