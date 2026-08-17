#!/usr/bin/env python3
"""Verifica el vínculo con la subcuenta de GoHighLevel.

Uso:
    export GHL_PRIVATE_TOKEN='pit-...'
    export GHL_LOCATION_ID='...'
    python3 scripts/verificar_conexion.py

Salida 0 = vínculo funcionando. Cualquier otro código = revisar el mensaje.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ghl import GHLAuthError, GHLClient, GHLError, GHLNetworkError  # noqa: E402


def main() -> int:
    try:
        client = GHLClient()
    except GHLError as exc:
        print(f"[config] {exc}")
        return 2

    print(f"Subcuenta: {client.location_id}")
    print(f"Token:     {client.token[:8]}...{client.token[-4:]}")
    print()

    checks = [
        ("Datos de la subcuenta", lambda: client.get_location()),
        ("Contactos (1 página)", lambda: client.list_contacts(limit=1)),
        ("Pipelines", lambda: client.list_pipelines()),
    ]

    failures = 0
    for label, call in checks:
        try:
            result = call()
        except GHLNetworkError as exc:
            print(f"  ✗ {label}: sin red\n    {exc}")
            return 3  # sin red no tiene sentido seguir probando
        except GHLAuthError as exc:
            print(f"  ✗ {label}: autenticación\n    {exc}")
            failures += 1
        except GHLError as exc:
            print(f"  ✗ {label}: {exc}")
            failures += 1
        else:
            print(f"  ✓ {label}: {resumen(result)}")

    print()
    if failures:
        print(f"{failures} de {len(checks)} verificaciones fallaron.")
        return 1
    print("Vínculo con GoHighLevel funcionando.")
    return 0


def resumen(result: dict) -> str:
    if "location" in result:
        loc = result["location"] or {}
        return f"{loc.get('name', '(sin nombre)')} — {loc.get('country', '?')}"
    if "contacts" in result:
        return f"{len(result['contacts'])} contacto(s), total {result.get('meta', {}).get('total', '?')}"
    if "pipelines" in result:
        nombres = [p.get("name", "?") for p in result["pipelines"][:3]]
        return f"{len(result['pipelines'])} pipeline(s): {', '.join(nombres)}"
    return "OK"


if __name__ == "__main__":
    sys.exit(main())
