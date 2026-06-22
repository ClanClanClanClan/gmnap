"""Python SDK for the GMNAP / MathLineage HTTP API.

Two ways to use it:

  - ``gmnap.sdk.Client`` — synchronous (requests-style, uses httpx)
  - ``gmnap.sdk.AsyncClient`` — async (httpx.AsyncClient)

Both share the same surface:

    >>> from src.sdk import Client
    >>> c = Client("http://localhost:8080")
    >>> entry = c.query("Hilbert, David")
    >>> entry["region_code"]
    'A2'
    >>> entry["BirthYear"]
    1862
    >>> for edge in c.lineage("name:Euler, Leonhard", depth=3):
    ...     print(edge)

Authentication: if the server is running with the V7 spec §12
hashcash gate enabled (default for prod), the SDK mints a valid
``X-Hashcash`` stamp for every request automatically. Operators can
also pass ``token=`` for the paid-tier Bearer-token path which
bypasses hashcash entirely. Local-dev servers running with
``GMNAP_REQUIRE_HASHCASH=0`` work without either.

Retries: the SDK retries network errors and 5xx responses 3 times
with exponential backoff (0.5 s → 1 s → 2 s); 429 (rate-limited) is
retried once with a 60-second wait. 4xx errors except 429 propagate
as ``GmnapClientError`` immediately.
"""

from .client import (
    AsyncClient,
    Client,
    GmnapAPIError,
    GmnapClientError,
    GmnapServerError,
    mint_hashcash,
)

__all__ = [
    "AsyncClient",
    "Client",
    "GmnapAPIError",
    "GmnapClientError",
    "GmnapServerError",
    "mint_hashcash",
]
