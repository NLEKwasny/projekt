"""Wspólne narzędzia: HTTP (stdlib urllib) i odczyt XML bez przestrzeni nazw."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Any

DEFAULT_UA = "Mozilla/5.0 (compatible; portfolio-agents/1.0)"
RETRY_STATUS = {429, 500, 502, 503, 504}


class HttpError(RuntimeError):
    pass


def get_bytes(url: str, *, user_agent: str = DEFAULT_UA, timeout: float = 20.0, retries: int = 2) -> bytes:
    last: Exception | None = None
    for attempt in range(retries + 1):
        request = urllib.request.Request(url, headers={"User-Agent": user_agent, "Accept": "*/*"})
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read()
        except urllib.error.HTTPError as exc:
            last = exc
            if exc.code not in RETRY_STATUS:
                break
        except urllib.error.URLError as exc:
            last = exc
        if attempt < retries:
            time.sleep(1.5 * (attempt + 1))
    raise HttpError(f"GET {url} nieudany: {last}")


def get_json(url: str, **kwargs: Any) -> Any:
    return json.loads(get_bytes(url, **kwargs))


def post_json(url: str, payload: dict[str, Any], *, timeout: float = 20.0) -> bytes:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "User-Agent": DEFAULT_UA},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        raise HttpError(f"POST {url} nieudany: {exc.code} {exc.reason}") from exc


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def find_text(elem: Any, name: str) -> str:
    """Tekst pierwszego potomka o nazwie `name`. Gdy węzeł ma dziecko <value>, zwraca jego tekst."""
    for node in elem.iter():
        if local_name(node.tag) == name:
            value = next((child for child in node if local_name(child.tag) == "value"), None)
            source = value if value is not None else node
            return (source.text or "").strip()
    return ""


def to_float(text: str) -> float:
    try:
        return float(text.replace(",", ""))
    except ValueError:
        return 0.0
