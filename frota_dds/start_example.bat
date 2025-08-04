@echo off
REM start_example.bat - Script de inicialização para Windows
REM Sistema de Monitoramento de Frota com Cyclone DDS

echo ========================================
echo Sistema de Monitoramento de Frota
echo Cyclone DDS - Exemplo Pratico
echo ========================================
echo.

REM Verificar se Python está instalado
python --version >nul 2>&1
if errorlevel 1 (
    echo ERRO: Python nao encontrado!
    echo Instale Python 3.8+ antes de continuar.
    pause
    exit /b 1
)

echo Python encontrado: 
python --version
echo.

REM Navegar para o diretório do script
cd /d "%~dp0"

echo Diretorio atual: %CD%
echo.

REM Verificar se os arquivos necessários existem
if not exist "run_example.py" (
    echo ERRO: Arquivo run_example.py nao encontrado!
    pause
    exit /b 1
)

if not exist "requirements.txt" (
    echo ERRO: Arquivo requirements.txt nao encontrado!
    pause
    exit /b 1
)

echo Arquivos do projeto encontrados.
echo.

REM Perguntar se deseja instalar dependências
set /p install_deps="Deseja verificar/instalar dependencias? (s/n): "
if /i "%install_deps%"=="s" (
    echo.
    echo Instalando dependencias...
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo AVISO: Algumas dependencias podem nao ter sido instaladas.
        echo Verifique manualmente se necessario.
    ) else (
        echo.
        echo Dependencias instaladas com sucesso!
    )
    echo.
)

REM Executar o programa principal
echo Iniciando sistema...
echo.
python run_example.py

REM Pausa final
echo.
echo Sistema finalizado.
pause