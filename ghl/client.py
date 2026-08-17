"""Cliente de la API v2 de GoHighLevel (LeadConnector).

Sólo usa la biblioteca estándar: no requiere instalar dependencias.

Autenticación por Private Integration Token (PIT). El token y el Location ID
se leen de variables de entorno; nunca se escriben en el repositorio.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

BASE_URL = "https://services.leadconnectorhq.com"

# Version es obligatorio en la API v2; sin este header la API responde 401.
API_VERSION = "2021-07-28"


class GHLError(Exception):
    """Error genérico de la API de GoHighLevel."""


class GHLAuthError(GHLError):
    """Token inválido, revocado o sin los scopes necesarios."""


class GHLNetworkError(GHLError):
    """No se pudo alcanzar la API (DNS, proxy de egreso, timeout)."""


class GHLClient:
    def __init__(
        self,
        token: str | None = None,
        location_id: str | None = None,
        *,
        base_url: str = BASE_URL,
        timeout: float = 30.0,
        max_retries: int = 3,
    ) -> None:
        self.token = token or os.environ.get("GHL_PRIVATE_TOKEN", "")
        self.location_id = location_id or os.environ.get("GHL_LOCATION_ID", "")
        if not self.token:
            raise GHLError(
                "Falta el Private Integration Token. "
                "Definí GHL_PRIVATE_TOKEN (el valor empieza con 'pit-')."
            )
        if not self.token.startswith("pit-"):
            raise GHLError(
                "GHL_PRIVATE_TOKEN no parece un Private Integration Token: "
                "el valor debe empezar con 'pit-'. "
                "Es fácil invertirlo con el Location ID."
            )
        if not self.location_id:
            raise GHLError("Falta el Location ID. Definí GHL_LOCATION_ID.")
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries

    # -- transporte ----------------------------------------------------------

    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict | None = None,
        body: dict | None = None,
    ) -> dict:
        url = f"{self.base_url}/{path.lstrip('/')}"
        if params:
            clean = {k: v for k, v in params.items() if v is not None}
            if clean:
                url = f"{url}?{urllib.parse.urlencode(clean)}"

        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(url, data=data, method=method.upper())
        req.add_header("Authorization", f"Bearer {self.token}")
        req.add_header("Version", API_VERSION)
        req.add_header("Accept", "application/json")
        if data is not None:
            req.add_header("Content-Type", "application/json")

        last_error: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    raw = resp.read().decode() or "{}"
                    return json.loads(raw)
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode(errors="replace")[:500]
                if exc.code in (401, 403):
                    raise GHLAuthError(
                        f"{exc.code} de la API: token inválido, revocado o sin el "
                        f"scope requerido para {method.upper()} {path}. {detail}"
                    ) from exc
                # 429 y 5xx son transitorios: reintento con backoff exponencial.
                if exc.code == 429 or exc.code >= 500:
                    last_error = exc
                    if attempt < self.max_retries - 1:
                        time.sleep(2**attempt)
                        continue
                raise GHLError(f"{exc.code} en {method.upper()} {path}: {detail}") from exc
            except urllib.error.URLError as exc:
                # El proxy de egreso responde 403 al CONNECT cuando el dominio
                # no está permitido; se manifiesta como URLError, no HTTPError.
                raise GHLNetworkError(
                    f"No se pudo alcanzar {self.base_url}: {exc.reason}. "
                    "Si estás en un entorno con proxy de egreso, hay que permitir "
                    "el dominio services.leadconnectorhq.com en la política de red."
                ) from exc

        raise GHLError(f"Falló {method.upper()} {path} tras {self.max_retries} intentos: {last_error}")

    def get(self, path: str, **params) -> dict:
        return self.request("GET", path, params=params)

    def post(self, path: str, body: dict) -> dict:
        return self.request("POST", path, body=body)

    # -- endpoints -----------------------------------------------------------

    def get_location(self) -> dict:
        """Datos de la subcuenta. Es la llamada más barata para validar el vínculo."""
        return self.get(f"/locations/{self.location_id}")

    def list_contacts(self, limit: int = 20, start_after_id: str | None = None) -> dict:
        return self.get(
            "/contacts/",
            locationId=self.location_id,
            limit=limit,
            startAfterId=start_after_id,
        )

    def iter_contacts(self, page_size: int = 100):
        """Recorre todos los contactos paginando por startAfterId."""
        after: str | None = None
        while True:
            page = self.list_contacts(limit=page_size, start_after_id=after)
            contacts = page.get("contacts") or []
            if not contacts:
                return
            yield from contacts
            after = contacts[-1].get("id")
            if not after or len(contacts) < page_size:
                return

    def list_pipelines(self) -> dict:
        return self.get("/opportunities/pipelines", locationId=self.location_id)

    def search_opportunities(self, limit: int = 20) -> dict:
        return self.get("/opportunities/search", location_id=self.location_id, limit=limit)

    def upsert_contact(self, **fields) -> dict:
        """Crea o actualiza un contacto (deduplica por email/teléfono)."""
        return self.post("/contacts/upsert", {"locationId": self.location_id, **fields})
