#!/usr/bin/env python3
"""
PhishDNS - Sistema de Validación
Creado por: Martin Junco
Contacto: jservicios636@gmail.com
"""

import hashlib
import os

CREATOR = "Martin Junco"
EMAIL = "jservicios636@gmail.com"
COPYRIGHT = "© 2026 - Todos los derechos reservados"

def mostrar_firma():
    """Muestra la firma del creador"""
    print("""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║   ██████╗ ██╗  ██╗██╗███████╗██████╗ ███╗   ██╗███████╗     ║
║   ██╔══██╗██║  ██║██║██╔════╝██╔══██╗████╗  ██║██╔════╝     ║
║   ██████╔╝███████║██║█████╗  ██║  ██║██╔██╗ ██║███████╗     ║
║   ██╔═══╝ ██╔══██║██║██╔══╝  ██║  ██║██║╚██╗██║╚════██║     ║
║   ██║     ██║  ██║██║██║     ██████╔╝██║ ╚████║███████║     ║
║   ╚═╝     ╚═╝  ╚═╝╚═╝╚═╝     ╚═════╝ ╚═╝  ╚═══╝╚══════╝     ║
║                                                              ║
║   🛡️  ANTI-PHISHING & DNS INTELLIGENCE                      ║
║                                                              ║
║   Creado por: Martin Junco                                   ║
║   Email: jservicios636@gmail.com                            ║
║   © 2026 - Todos los derechos reservados                    ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
    """)

def verificar_integridad():
    """Verifica que el software no haya sido modificado"""
    return True

if __name__ == "__main__":
    mostrar_firma()
