#!/usr/bin/env python3
"""
Script para ejecutar tests de manera fácil.
"""

import sys
import os
import subprocess
import argparse

# Agregar el directorio backend al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def run_tests(test_type=None, verbose=False):
    """Ejecuta los tests especificados."""
    
    # Comandos base
    base_cmd = ["python", "-m", "pytest"]
    
    if verbose:
        base_cmd.append("-v")
    
    # Determinar qué tests ejecutar
    if test_type == "services":
        test_path = "app/tests/services/"
        print("🧪 Ejecutando tests de servicios...")
    elif test_type == "api":
        test_path = "app/tests/api/"
        print("🧪 Ejecutando tests de API...")
    elif test_type == "all":
        test_path = "app/tests/"
        print("🧪 Ejecutando todos los tests...")
    else:
        print("❌ Tipo de test no especificado. Usa: services, api, o all")
        return False
    
    # Construir comando completo
    cmd = base_cmd + [test_path]
    
    print(f"📋 Comando: {' '.join(cmd)}")
    print("=" * 50)
    
    try:
        # Ejecutar tests
        result = subprocess.run(cmd, cwd=os.path.join(os.path.dirname(__file__), '..'))
        
        if result.returncode == 0:
            print("\n✅ Tests completados exitosamente!")
        else:
            print("\n❌ Algunos tests fallaron.")
        
        return result.returncode == 0
        
    except Exception as e:
        print(f"❌ Error ejecutando tests: {str(e)}")
        return False

def run_manual_test(test_file):
    """Ejecuta un test manual específico."""
    
    test_path = f"app/tests/services/{test_file}"
    
    if not os.path.exists(os.path.join(os.path.dirname(__file__), '..', test_path)):
        print(f"❌ Archivo de test no encontrado: {test_path}")
        return False
    
    print(f"🧪 Ejecutando test manual: {test_file}")
    print("=" * 50)
    
    try:
        # Ejecutar test manual
        cmd = ["python", test_path]
        result = subprocess.run(cmd, cwd=os.path.join(os.path.dirname(__file__), '..'))
        
        if result.returncode == 0:
            print("\n✅ Test manual completado exitosamente!")
        else:
            print("\n❌ Test manual falló.")
        
        return result.returncode == 0
        
    except Exception as e:
        print(f"❌ Error ejecutando test manual: {str(e)}")
        return False

def main():
    """Función principal."""
    
    parser = argparse.ArgumentParser(description="Ejecutar tests de la aplicación")
    parser.add_argument(
        "type", 
        choices=["services", "api", "all", "manual"],
        help="Tipo de tests a ejecutar"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Ejecutar en modo verbose"
    )
    parser.add_argument(
        "--file", "-f",
        help="Archivo de test específico para modo manual"
    )
    
    args = parser.parse_args()
    
    if args.type == "manual":
        if not args.file:
            print("❌ Para modo manual, especifica un archivo con --file")
            print("Archivos disponibles:")
            print("  - test_slack_user_service.py")
            print("  - test_slack_response_scheduler.py")
            print("  - test_ai_service.py")
            return False
        
        success = run_manual_test(args.file)
    else:
        success = run_tests(args.type, args.verbose)
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 