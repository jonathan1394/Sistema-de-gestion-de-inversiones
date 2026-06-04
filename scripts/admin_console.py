#!/usr/bin/env python3
"""Administrative console for CriptoLab system."""

from __future__ import annotations

import subprocess
import sys
from typing import Dict, List

from app.logging_setup import setup_logging


def load_settings():
    """Load settings from the app package."""
    try:
        from app.config import load_settings as load_app_settings

        return load_app_settings()
    except ImportError:
        # Fallback for when not run as module
        import os

        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from app.config import load_settings as load_app_settings

        return load_app_settings()


def print_header():
    """Print console header."""
    settings = load_settings()
    print("=" * 60)
    print("🧪 CriptoLab Administrative Console")
    print("=" * 60)
    print(
        f"Mode: {settings.mode} | Kill Switch: {'ACTIVE' if settings.kill_switch else 'INACTIVE'}"
    )
    print("=" * 60)


def print_menu(options: Dict[str, str]):
    """Print menu options."""
    for key, description in options.items():
        print(f"{key}. {description}")
    print("0. Exit")
    print("-" * 40)


def run_command(cmd: List[str], description: str):
    """Run a command and display results."""
    print(f"\n🔄 Ejecutando: {description}")
    print("-" * 50)
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        print(f"✅ Completado: {description}")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error ejecutando {description}:")
        print(f"Return code: {e.returncode}")
        if e.stdout:
            print("STDOUT:", e.stdout)
        if e.stderr:
            print("STDERR:", e.stderr)
    except FileNotFoundError:
        print(f"❌ Comando no encontrado: {' '.join(cmd)}")
    print("-" * 50)


def _prompt(desc: str, default: str = "") -> str:
    return input(f"{desc} (default: {default}): ").strip() or default


def _handle_daily_report() -> None:
    run_command([sys.executable, "-m", "scripts.daily_report"], "Generando reporte diario")


def _handle_alert_monitor() -> None:
    symbol = _prompt("Símbolo para monitorear", "BTCUSDT")
    interval = _prompt("Intervalo en segundos", "30")
    run_command(
        [sys.executable, "-m", "scripts.alert_monitor", "--symbol", symbol, "--interval", interval],
        f"Iniciando monitor de alertas para {symbol}",
    )


def _handle_view_decisions() -> None:
    limit_raw = input("Número de decisiones a mostrar (default: 20): ").strip()
    limit = int(limit_raw) if limit_raw.isdigit() else 20
    run_command(
        [sys.executable, "-m", "scripts.view_decisions", "--limit", str(limit)],
        "Mostrando registro de decisiones",
    )


def _handle_generate_ranking() -> None:
    symbols = _prompt("Símbolos (coma-separados)", "BTCUSDT,ETHUSDT,SOLUSDT")
    interval = _prompt("Intervalo", "1h")
    limit_raw = input("Límite (default: 10): ").strip()
    limit = int(limit_raw) if limit_raw.isdigit() else 10
    run_command(
        [sys.executable, "-m", "scripts.generate_ranking", "--symbols", symbols, "--interval", interval, "--limit", str(limit)],
        "Generando ranking de activos",
    )


def _handle_paper_trading() -> None:
    symbol = _prompt("Símbolo", "BTCUSDT")
    interval = _prompt("Intervalo", "1h")
    strategy = _prompt("Estrategia (ma/rsi/trend)", "ma")
    fast = _prompt("Período rápido", "20")
    slow = _prompt("Período lento", "50")
    run_command(
        [sys.executable, "-m", "scripts.run_paper_trading", "--symbol", symbol, "--interval", interval, "--strategy", strategy, "--fast", fast, "--slow", slow],
        "Ejecutando paper trading",
    )


def _handle_download() -> None:
    symbol = _prompt("Símbolo", "BTCUSDT")
    interval = _prompt("Intervalo", "1h")
    limit_raw = input("Límite (default: 1000): ").strip()
    limit = int(limit_raw) if limit_raw.isdigit() else 1000
    run_command(
        [sys.executable, "-m", "scripts.download_historical", "--symbol", symbol, "--interval", interval, "--limit", str(limit)],
        "Descargando datos históricos",
    )


def _handle_prospecting() -> None:
    symbols = _prompt("Símbolos (coma-separados)", "BTCUSDT,ETHUSDT,SOLUSDT")
    interval = _prompt("Intervalo", "1d")
    run_command(
        [sys.executable, "-m", "scripts.run_prospecting", "--symbols", symbols, "--interval", interval],
        "Ejecutando prospecting y scoring",
    )


def _handle_compare_backtests() -> None:
    print("\nArchivos de métricas disponibles en ./reports/backtests/")
    files_input = input("Archivos JSON (coma-separados, o dejar vacío para ejemplos): ").strip()
    if files_input:
        files = [f.strip() for f in files_input.split(",")]
        run_command([sys.executable, "-m", "scripts.compare_backtests", "--files"] + files, "Comparando backtests")
    else:
        print("💡 Ejemplo: python -m scripts.compare_backtests --files ./reports/backtests/btc_1h_ma/metrics.json ./reports/backtests/eth_4h_ma/metrics.json")


def _handle_compare_strategies() -> None:
    symbols = _prompt("Símbolos (coma-separados)", "BTCUSDT,ETHUSDT")
    intervals = _prompt("Intervalos (coma-separados)", "1h,4h")
    strategies = _prompt("Estrategias (coma-separados)", "ma,rsi,trend")
    run_command(
        [sys.executable, "-m", "scripts.compare_strategies", "--symbols", symbols, "--intervals", intervals, "--strategies", strategies],
        "Comparando estrategias",
    )


def _handle_quality() -> None:
    run_command([sys.executable, "-m", "quality.quality_agent", "--check-all"], "Ejecutando quality gate completo")


def _handle_tests() -> None:
    run_command([sys.executable, "-m", "pytest"], "Ejecutando suite de pruebas")


def _handle_dashboard() -> None:
    print("\n🚀 Iniciando Dashboard Streamlit...")
    print("📍 El dashboard estará disponible en: http://localhost:8501")
    print("💡 Presiona Ctrl+C para detener el dashboard y volver al menú")
    try:
        subprocess.run([sys.executable, "-m", "streamlit", "run", "app/dashboard/main.py"])
    except KeyboardInterrupt:
        print("\n👋 Dashboard detenido. Volviendo al menú...")


MENU_ITEMS: list[tuple[str, str, callable]] = [
    ("1", "📊 Generar Reporte Diario", _handle_daily_report),
    ("2", "🔔 Iniciar Monitor de Alertas", _handle_alert_monitor),
    ("3", "📋 Ver Registro de Decisiones", _handle_view_decisions),
    ("4", "📈 Generar Ranking de Activos", _handle_generate_ranking),
    ("5", "💰 Ejecutar Paper Trading", _handle_paper_trading),
    ("6", "📥 Descargar Datos Históricos", _handle_download),
    ("7", "🔍 Ejecutar Prospecting y Scoring", _handle_prospecting),
    ("8", "⚖️ Comparar Backtests", _handle_compare_backtests),
    ("9", "🎯 Comparar Estrategias", _handle_compare_strategies),
    ("10", "🧪 Ejecutar Pruebas de Calidad", _handle_quality),
    ("11", "🐛 Ejecutar Test Suite", _handle_tests),
    ("12", "🖥️  Iniciar Dashboard Streamlit", _handle_dashboard),
]

MENU_MAP: dict[str, callable] = {key: handler for key, _, handler in MENU_ITEMS}


def main_menu():
    """Display main menu and handle user selection."""
    options = {key: desc for key, desc, _ in MENU_ITEMS}

    while True:
        print_header()
        print_menu(options)

        choice = input("Selecciona una opción: ").strip()

        if choice == "0":
            print("👋 ¡Hasta luego!")
            break

        handler = MENU_MAP.get(choice)
        if handler:
            handler()
        else:
            print("❌ Opción no válida. Por favor, selecciona un número del menú.")

        input("\nPresiona ENTER para continuar...")


if __name__ == "__main__":
    setup_logging()
    try:
        main_menu()
    except KeyboardInterrupt:
        print("\n👋 ¡Hasta luego!")
        sys.exit(0)
