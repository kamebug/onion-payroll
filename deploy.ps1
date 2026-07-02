# deploy.ps1 - Onion Payroll
# Uso: powershell -ExecutionPolicy Bypass -File ".\deploy.ps1"

$FLET   = "C:\Users\kameo\AppData\Local\Programs\Python\Python311\Scripts\flet.exe"
$REPO   = "onion-payroll"
$ROOT   = $PSScriptRoot

Write-Host ""
Write-Host "Onion Payroll - Deploy" -ForegroundColor Cyan
Write-Host "----------------------" -ForegroundColor DarkGray

# 1. Gerar BUILD_ID com data/hora atual
$BUILD_ID = Get-Date -Format "yyMMddHHmm"
Write-Host "Build ID: $BUILD_ID" -ForegroundColor Cyan

(Get-Content "$ROOT\main.py") -replace 'BUILD_ID\s*=\s*"[0-9]*".*', "BUILD_ID       = `"$BUILD_ID`"   # atualizado automaticamente pelo deploy.ps1" | Set-Content "$ROOT\main.py"
Write-Host "BUILD_ID atualizado no main.py" -ForegroundColor Green

# 2. Limpar pastas anteriores
Write-Host ""
Write-Host "Limpando..." -ForegroundColor Yellow
Remove-Item -Recurse -Force "$ROOT\build_src" -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force "$ROOT\docs" -ErrorAction SilentlyContinue

# 3. Criar pasta limpa
Write-Host "Criando pasta limpa..." -ForegroundColor Yellow
New-Item -ItemType Directory -Path "$ROOT\build_src" -Force | Out-Null
Copy-Item "$ROOT\main.py"          "$ROOT\build_src\"
Copy-Item "$ROOT\requirements.txt" "$ROOT\build_src\"
Copy-Item "$ROOT\pyproject.toml"   "$ROOT\build_src\"
Copy-Item "$ROOT\assets"           "$ROOT\build_src\assets" -Recurse -Force

# 4. Build na pasta limpa
Write-Host ""
Write-Host "Gerando build web..." -ForegroundColor Cyan
Set-Location "$ROOT\build_src"
& $FLET build web --base-url /$REPO

if ($LASTEXITCODE -ne 0) {
    Set-Location $ROOT
    Write-Host "ERRO: Build falhou." -ForegroundColor Red
    Read-Host "Pressione Enter para fechar"
    exit 1
}

# 5. Verificar tamanho do app.zip
$zipSize = (Get-Item "$ROOT\build_src\build\web\assets\app\app.zip").Length / 1MB
Write-Host "app.zip: $([math]::Round($zipSize, 2)) MB" -ForegroundColor Cyan
if ($zipSize -gt 90) {
    Set-Location $ROOT
    Write-Host "ERRO: app.zip maior que 90MB!" -ForegroundColor Red
    Read-Host "Pressione Enter para fechar"
    exit 1
}

# 6. Copiar para docs/
Write-Host "Copiando para docs/..." -ForegroundColor Cyan
New-Item -ItemType Directory -Path "$ROOT\docs" -Force | Out-Null
Copy-Item -Path "$ROOT\build_src\build\web\*" -Destination "$ROOT\docs\" -Recurse -Force

# 7. Adicionar Analytics + meta tags anti-cache no index.html
$headInjection = @"
  <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
  <meta http-equiv="Pragma" content="no-cache">
  <meta http-equiv="Expires" content="0">
  <!-- Google Analytics -->
  <script async src="https://www.googletagmanager.com/gtag/js?id=G-2Z4173R5NS"></script>
  <script>
    window.dataLayer = window.dataLayer || [];
    function gtag(){dataLayer.push(arguments);}
    gtag('js', new Date());
    gtag('config', 'G-2Z4173R5NS');
  </script>
"@
$html = Get-Content "$ROOT\docs\index.html" -Raw
$html = $html -replace "</head>", "$headInjection`n</head>"

# Libera pinch-to-zoom — o Flet gera o viewport com maximum-scale=1.0 e
# user-scalable=no por padrao, bloqueando o zoom nativo do navegador.
# Corrigido aqui automaticamente a cada deploy (nao precisa mais editar
# docs/index.html na mao depois de cada build).
$html = $html -replace ',\s*maximum-scale=1\.0,\s*user-scalable=no', ''

$html | Set-Content "$ROOT\docs\index.html" -Encoding UTF8
Write-Host "Analytics, meta tags anti-cache e zoom liberado no index.html" -ForegroundColor Green

# 8. Limpar build_src
Set-Location $ROOT
Remove-Item -Recurse -Force "$ROOT\build_src"
$docsSize = [math]::Round((Get-ChildItem "$ROOT\docs" -Recurse | Measure-Object Length -Sum).Sum / 1MB, 1)
Write-Host "docs/: $docsSize MB" -ForegroundColor Green

# 9. Git push
Write-Host ""
$MSG = Read-Host "Mensagem do commit (Enter = Deploy $BUILD_ID)"
if ([string]::IsNullOrWhiteSpace($MSG)) { $MSG = "Deploy $BUILD_ID" }

git add docs\ main.py
git commit -m $MSG
git push

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERRO: Push falhou." -ForegroundColor Red
    Read-Host "Pressione Enter para fechar"
    exit 1
}

Write-Host ""
Write-Host "Deploy concluido! Build: $BUILD_ID" -ForegroundColor Green
Write-Host "https://kamebug.github.io/$REPO/" -ForegroundColor Cyan
Write-Host ""
Write-Host "DICA: se o app nao atualizar, force refresh com Ctrl+Shift+R" -ForegroundColor Yellow
Write-Host "ou limpe cache do navegador no celular." -ForegroundColor Yellow
Write-Host ""
Read-Host "Pressione Enter para fechar"
