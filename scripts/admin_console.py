#!/usr/bin/env python3
"""Administrative console for CriptoLab system."""

from __future__ import annotations

import logging
import subprocess
import sys
from typing import Dict, List

from app.logging_setup import setup_logging

logger = logging.getLogger(__name__)

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
    print(f"Mode: {settings.mode} | Kill Switch: {'ACTIVE' if settings.kill_switch else 'INACTIVE'}")
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


def main_menu():
    """Display main menu and handle user selection."""
    options = {
        "1": "📊 Generar Reporte Diario",
        "2": "🔔 Iniciar Monitor de Alertas",
        "3": "📋 Ver Registro de Decisiones",
        "4": "📈 Generar Ranking de Activos",
        "5": "💰 Ejecutar Paper Trading",
        "6": "📥 Descargar Datos Históricos",
        "7": "🔍 Ejecutar Prospecting y Scoring",
        "8": "⚖️ Comparar Backtests",
        "9": "🎯 Comparar Estrategias",
        "10": "🧪 Ejecutar Pruebas de Calidad",
        "11": "🐛 Ejecutar Test Suite",
        "12": "🖥️  Iniciar Dashboard Streamlit",
    }

    while True:
        print_header()
        print_menu(options)

        choice = input("Selecciona una opción: ").strip()

        if choice == "0":
            print("👋 ¡Hasta luego!")
            break
        elif choice == "1":
            run_command([sys.executable, "-m", "scripts.daily_report"], "Generando reporte diario")
        elif choice == "2":
            symbol = input("Símbolo para monitorear (default: BTCUSDT): ").strip() or "BTCUSDT"
            interval = input("Intervalo en segundos (default: 30): ").strip() or "30"
            run_command([
                sys.executable, "-m", "scripts.alert_monitor",
                "--symbol", symbol,
                "--interval", interval
            ], f"Iniciando monitor de alertas para {symbol}")
        elif choice == "3":
            limit_input = input("Número de decisiones a mostrar (default: 20): ").strip()
            limit = int(limit_input) if limit_input.isdigit() else 20
            run_command([
                sys.executable, "-m", "scripts.view_decisions",
                "--limit", str(limit)
            ], "Mostrando registro de decisiones")
        elif choice == "4":
            symbols_input = input("Símbolos (coma-separados, default: BTCUSDT,ETHUSDT,SOLUSDT): ").strip()
            symbols = symbols_input or "BTCUSDT,ETHUSDT,SOLUSDT"
            interval = input("Intervalo (default: 1h): ").strip() or "1h"
            limit_input = input("Límite (default: 10): ").strip()
            limit = int(limit_input) if limit_input.isdigit() else 10
            run_command([
                sys.executable, "-m", "scripts.generate_ranking",
                "--symbols", symbols,
                "--interval", interval,
                "--limit", str(limit)
            ], "Generando ranking de activos")
        elif choice == "5":
            symbol = input("Símbolo (default: BTCUSDT): ").strip() or "BTCUSDT"
            interval = input("Intervalo (default: 1h): ").strip() or "1h"
            strategy = input("Estrategia (ma/rsi/trend - default: ma): ").strip() or "ma"
            fast = input("Período rápido (default: 20): ").strip() or "20"
            slow = input("Período lento (default: 50): ").strip() or "50"
            run_command([
                sys.executable, "-m", "scripts.run_paper_trading",
                "--symbol", symbol,
                "--interval", interval,
                "--strategy", strategy,
                "--fast", fast,
                "--slow", slow
            ], "Ejecutando paper trading")
        elif choice == "6":
            symbol = input("Símbolo (default: BTCUSDT): ").strip() or "BTCUSDT"
            interval = input("Intervalo (default: 1h): ").strip() or "1h"
            limit_input = input("Límite (default: 1000): ").strip()
            limit = int(limit_input) if limit_input.isdigit() else 1000
            run_command([
                sys.executable, "-m", "scripts.download_historical",
                "--symbol", symbol,
                "--interval", interval,
                "--limit", limit
            ], "Descargando datos históricos")
        elif choice == "7":
            symbols_input = input("Símbolos (coma-separados, default: BTCUSDT,ETHUSDT,SOLUSDT): ").strip()
            symbols = symbols_input or "BTCUSDT,ETHUSDT,SOLUSDT"
            interval = input("Intervalo (default: 1d): ").strip() or "1d"
            run_command([
                sys.executable, "-m", "scripts.run_prospecting",
                "--symbols", symbols,
                "--interval", interval
            ], "Ejecutando prospecting y scoring")
        elif choice == "8":
            print("\nArchivos de métricas disponibles en ./reports/backtests/")
            files_input = input("Archivos JSON (coma-separados, o dejar vacío para ejemplos): ").strip()
            if files_input:
                files = [f.strip() for f in files_input.split(",")]
                cmd = [sys.executable, "-m", "scripts.compare_backtests", "--files"] + files
                run_command(cmd, "Comparando backtests")
            else:
                print("💡 Ejemplo: python -m scripts.compare_backtests --files ./reports/backtests/btc_1h_ma/metrics.json ./reports/backtests/eth_4h_ma/metrics.json")
        elif choice == "9":
            symbols_input = input("Símbolos (coma-separados, default: BTCUSDT,ETHUSDT): ").strip()
            symbols = symbols_input or "BTCUSDT,ETHUSDT"
            intervals_input = input("Intervalos (coma-separados, default: 1h,4h): ").strip()
            intervals = intervals_input or "1h,4h"
            strategies_input = input("Estrategias (coma-separados, default: ma,rsi,trend): ").strip()
            strategies = strategies_input or "ma,rsi,trend"
            run_command([
                sys.executable, "-m", "scripts.compare_strategies",
                "--symbols", symbols,
                "--intervals", intervals,
                "--strategies", strategies
            ], "Comparando estrategias")
        elif choice == "10":
            run_command([sys.executable, "-m", "quality.quality_agent", "--check-all"], "Ejecutando quality gate completo")
        elif choice == "11":
            run_command([sys.executable, "-m", "pytest"], "Ejecutando suite de pruebas")
        elif choice == "12":
            print("\n🚀 Iniciando Dashboard Streamlit...")
            print("📍 El dashboard estará disponible en: http://localhost:8501")
            print("💡 Presiona Ctrl+C para detener el dashboard y volver al menú")
            try:
                subprocess.run([sys.executable, "-m", "streamlit", "run", "app/dashboard/main.py"])
            except KeyboardInterrupt:
                print("\n👋 Dashboard detenido. Volviendo al menú...")
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
