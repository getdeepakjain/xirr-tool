"""Market price refresh for unit-priced holdings.

Best-effort fetching of the latest market price/NAV for MF, Stocks and Crypto
holdings from free public sources:

* MF     -> AMFI daily NAV file (https://www.amfiindia.com/spages/NAVAll.txt)
* Stocks -> Yahoo Finance chart API (symbol parsed from the linked-data name)
* Crypto -> CoinGecko simple price API (INR)

Every network call is wrapped so a failure for one holding (or one provider)
never aborts the whole refresh; such holdings are simply reported as skipped.
The pure parsing/matching helpers are import-safe and network-free so they can
be unit tested in isolation.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

import httpx

from .constants import AssetClass
from .models import Holding

_TIMEOUT = 12.0
_USER_AGENT = "xirr-tool/1.0 (portfolio price refresh)"

# Map an Exchange MIC (as it appears in Excel Stocks names, e.g. "XNSE:INFY")
# to the suffix Yahoo Finance expects.
_YAHOO_SUFFIX = {
    "XNSE": ".NS",
    "XNAS": "",
    "XNYS": "",
    "XBOM": ".BO",
    "XBSE": ".BO",
}

# ---------------------------------------------------------------------------
# Name / symbol helpers (network-free, unit-testable)
# ---------------------------------------------------------------------------

# Words that add noise when matching MF scheme names.
_MF_NOISE = re.compile(
    r"\b(growth|reinvestment|payout|dividend|idcw|regular|direct|plan|option|"
    r"fund|scheme|the|an?)\b",
    re.IGNORECASE,
)
_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def normalize_mf_name(name: str) -> str:
    """Normalize an MF scheme name for fuzzy matching against AMFI data."""
    s = _MF_NOISE.sub(" ", (name or "").lower())
    s = _NON_ALNUM.sub(" ", s)
    return " ".join(s.split())


def parse_stock_symbol(name: str) -> str | None:
    """Extract a Yahoo Finance symbol from a linked-data stock name.

    e.g. ``"APOLLO HOSPITALS ENTERPRISE LIMITED (XNSE:APOLLOHOSP)"`` ->
    ``"APOLLOHOSP.NS"``. Returns ``None`` if no ``(MIC:TICKER)`` marker exists.
    """
    m = re.search(r"\(([A-Z]{2,6}):([A-Za-z0-9&.\-]+)\)", name or "")
    if not m:
        return None
    mic, ticker = m.group(1).upper(), m.group(2).upper()
    suffix = _YAHOO_SUFFIX.get(mic, ".NS")  # default to NSE for Indian data
    return f"{ticker}{suffix}"


def parse_amfi_navall(text: str) -> dict[str, float]:
    """Parse AMFI's NAVAll.txt into a ``{normalized_scheme_name: nav}`` map.

    The file is ``;``-separated with columns:
    ``Scheme Code;ISIN1;ISIN2;Scheme Name;Net Asset Value;Date``.
    """
    out: dict[str, float] = {}
    for line in text.splitlines():
        parts = line.split(";")
        if len(parts) < 6:
            continue
        scheme_name, nav_raw = parts[3].strip(), parts[4].strip()
        if not scheme_name or scheme_name.lower() == "scheme name":
            continue
        try:
            nav = float(nav_raw)
        except ValueError:
            continue
        key = normalize_mf_name(scheme_name)
        if key:
            out[key] = nav
    return out


def match_mf_nav(name: str, nav_map: dict[str, float]) -> float | None:
    """Find the best NAV for a scheme name within a parsed AMFI map."""
    key = normalize_mf_name(name)
    if not key:
        return None
    if key in nav_map:
        return nav_map[key]
    # Fall back to the longest AMFI name that contains (or is contained by) ours.
    best: tuple[int, float] | None = None
    for cand, nav in nav_map.items():
        if key in cand or cand in key:
            score = len(cand)
            if best is None or score > best[0]:
                best = (score, nav)
    return best[1] if best else None


# ---------------------------------------------------------------------------
# Network providers
# ---------------------------------------------------------------------------
@dataclass
class PriceResult:
    holding_id: int
    name: str
    asset_class: str
    old_price: float | None
    new_price: float | None
    status: str  # "updated" | "unchanged" | "not_found" | "error"
    detail: str = ""


def _client() -> httpx.Client:
    return httpx.Client(timeout=_TIMEOUT, headers={"User-Agent": _USER_AGENT})


class PriceService:
    """Fetches and caches reference data, then resolves prices per holding."""

    def __init__(self, client: httpx.Client | None = None):
        self._client = client or _client()
        self._owns_client = client is None
        self._mf_navs: dict[str, float] | None = None
        self._coin_ids: dict[str, str] | None = None

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> "PriceService":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    # -- MF -----------------------------------------------------------------
    def _mf_nav_map(self) -> dict[str, float]:
        if self._mf_navs is None:
            resp = self._client.get("https://www.amfiindia.com/spages/NAVAll.txt")
            resp.raise_for_status()
            self._mf_navs = parse_amfi_navall(resp.text)
        return self._mf_navs

    def mf_price(self, holding: Holding) -> float | None:
        return match_mf_nav(holding.name, self._mf_nav_map())

    # -- Stocks -------------------------------------------------------------
    def stock_price(self, holding: Holding) -> float | None:
        symbol = parse_stock_symbol(holding.name)
        if not symbol:
            return None
        resp = self._client.get(
            f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
        )
        resp.raise_for_status()
        result = (resp.json().get("chart", {}).get("result") or [None])[0]
        if not result:
            return None
        price = result.get("meta", {}).get("regularMarketPrice")
        return float(price) if price is not None else None

    # -- Crypto -------------------------------------------------------------
    def _coin_id_map(self) -> dict[str, str]:
        if self._coin_ids is None:
            resp = self._client.get("https://api.coingecko.com/api/v3/coins/list")
            resp.raise_for_status()
            ids: dict[str, str] = {}
            for coin in resp.json():
                sym = str(coin.get("symbol", "")).lower()
                # First occurrence wins (usually the canonical coin).
                ids.setdefault(sym, coin.get("id", ""))
                ids.setdefault(str(coin.get("name", "")).lower(), coin.get("id", ""))
            self._coin_ids = ids
        return self._coin_ids

    def crypto_price(self, holding: Holding) -> float | None:
        token = (holding.identifier or holding.name or "").strip().lower()
        coin_id = self._coin_id_map().get(token)
        if not coin_id:
            return None
        resp = self._client.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={"ids": coin_id, "vs_currencies": "inr"},
        )
        resp.raise_for_status()
        entry = resp.json().get(coin_id, {})
        return float(entry["inr"]) if "inr" in entry else None

    # -- Dispatch -----------------------------------------------------------
    def price_for(self, holding: Holding) -> float | None:
        if holding.asset_class == AssetClass.MF.value:
            return self.mf_price(holding)
        if holding.asset_class == AssetClass.STOCKS.value:
            return self.stock_price(holding)
        if holding.asset_class == AssetClass.CRYPTO.value:
            return self.crypto_price(holding)
        return None


# Asset classes we can refresh from a market source.
REFRESHABLE = {AssetClass.MF.value, AssetClass.STOCKS.value, AssetClass.CRYPTO.value}


def refresh_prices(holdings: list[Holding], service: PriceService | None = None) -> list[PriceResult]:
    """Refresh ``latest_price`` for each refreshable holding (best effort).

    Mutates ``holding.latest_price`` in place for successful lookups; the caller
    is responsible for committing the session.
    """
    targets = [h for h in holdings if h.asset_class in REFRESHABLE]
    if not targets:
        return []

    own = service is None
    service = service or PriceService()
    results: list[PriceResult] = []
    try:
        for h in targets:
            old = h.latest_price
            try:
                new = service.price_for(h)
            except Exception as exc:  # network / parsing issue for this holding
                results.append(PriceResult(h.id, h.name, h.asset_class, old, None,
                                           "error", str(exc)[:200]))
                continue
            if new is None:
                results.append(PriceResult(h.id, h.name, h.asset_class, old, None, "not_found"))
                continue
            if old is not None and abs(old - new) < 1e-9:
                results.append(PriceResult(h.id, h.name, h.asset_class, old, new, "unchanged"))
                continue
            h.latest_price = new
            results.append(PriceResult(h.id, h.name, h.asset_class, old, new, "updated"))
    finally:
        if own:
            service.close()
    return results
