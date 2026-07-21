"""Probe OpenAI bearer acceptance from secret stdin and emit only HTTP status."""

from __future__ import annotations

import http.client
import json
import sys


HOST = "api.openai.com"
PATH = "/v1/models"
SOCKET_TIMEOUT_SECONDS = 25
MAX_API_KEY_BYTES = 4096


def probe(api_key: str) -> int | None:
    connection: http.client.HTTPSConnection | None = None
    response: http.client.HTTPResponse | None = None
    status: int | None = None
    try:
        connection = http.client.HTTPSConnection(HOST, timeout=SOCKET_TIMEOUT_SECONDS)
        connection.request(
            "GET",
            PATH,
            headers={"Authorization": f"Bearer {api_key}"},
        )
        response = connection.getresponse()
        observed = response.status
        if isinstance(observed, int) and not isinstance(observed, bool):
            status = observed
    except (OSError, ValueError, http.client.HTTPException):
        status = None
    finally:
        if response is not None:
            try:
                response.close()
            except (OSError, ValueError, http.client.HTTPException):
                status = None
        if connection is not None:
            try:
                connection.close()
            except (OSError, ValueError, http.client.HTTPException):
                status = None
    return status


def main() -> int:
    raw = sys.stdin.buffer.read(MAX_API_KEY_BYTES + 1)
    if not raw or len(raw) > MAX_API_KEY_BYTES:
        status = None
    else:
        try:
            api_key = raw.decode("utf-8")
        except UnicodeDecodeError:
            status = None
        else:
            status = probe(api_key)
    sys.stdout.write(json.dumps({"status": status}, allow_nan=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
