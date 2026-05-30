from __future__ import annotations

import hashlib
import hmac
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

import requests

from app.config import AppConfig


@dataclass
class AccountBalance:
    asset: str
    free: float
    locked: float
    total: float


@dataclass
class OrderInfo:
    symbol: str
    order_id: int
    side: str
    type: str
    price: float
    orig_qty: float
    executed_qty: float
    status: str
    time: datetime


@dataclass
class PermissionCheck:
    can_trade: bool = False
    can_withdraw_assets: bool = False
    read_only: bool = True
    valid: bool = False
    message: str = ""


class BinanceExecutor:
    def __init__(
        self,
        config: AppConfig,
        api_key: str = "",
        api_secret: str = "",
    ) -> None:
        self._config = config
        self._api_key = api_key
        self._api_secret = api_secret
        self._base_url = config.binance.base_url or "https://api.binance.com"
        self._session = requests.Session()
        self._session.headers.update({
            "X-MBX-APIKEY": api_key,
            "Content-Type": "application/x-www-form-urlencoded",
        })
        self._mode = config.mode
        self._permissions: Optional[PermissionCheck] = None

    def validate_permissions(self) -> PermissionCheck:
        if not self._api_key:
            return PermissionCheck(
                valid=False,
                message="No API key configured. Set BINANCE_API_KEY in .env",
            )

        try:
            result = self._signed_get("/api/v3/account")
            if "canTrade" not in result:
                return PermissionCheck(valid=False, message="Invalid API response")

            perms = PermissionCheck(
                can_trade=result.get("canTrade", False),
                can_withdraw_assets=result.get("canWithdraw", False),
                read_only=result.get("canTrade", False) is False,
                valid=True,
                message="API permissions validated",
            )

            if perms.can_withdraw_assets:
                perms.message += " ⚠️ Withdraw permission enabled — disable immediately"
                perms.valid = False

            if self._mode in ("real_manual", "real_auto_limited") and not perms.can_trade:
                perms.message += " ⚠️ Trading mode enabled but API key lacks trade permission"
                perms.valid = False

            self._permissions = perms
            return perms

        except Exception as e:
            return PermissionCheck(valid=False, message=f"API validation failed: {e}")

    def get_balances(self) -> list[AccountBalance]:
        result = self._signed_get("/api/v3/account")
        balances = []
        for bal in result.get("balances", []):
            free = float(bal["free"])
            locked = float(bal["locked"])
            if free > 0 or locked > 0:
                balances.append(AccountBalance(
                    asset=bal["asset"],
                    free=free,
                    locked=locked,
                    total=free + locked,
                ))
        return balances

    def get_open_orders(self, symbol: str = "") -> list[OrderInfo]:
        params = {}
        if symbol:
            params["symbol"] = symbol.upper()
        result = self._signed_get("/api/v3/openOrders", params)
        return [self._parse_order(o) for o in result]

    def get_order_history(self, symbol: str, limit: int = 50) -> list[OrderInfo]:
        result = self._signed_get("/api/v3/allOrders", {
            "symbol": symbol.upper(),
            "limit": min(limit, 1000),
        })
        return [self._parse_order(o) for o in result]

    def get_server_time(self) -> int:
        resp = self._public_get("/api/v3/time")
        return int(resp["serverTime"])

    def check_connectivity(self) -> bool:
        try:
            self._public_get("/api/v3/ping")
            return True
        except requests.RequestException:
            return False

    def create_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        order_type: str = "MARKET",
        price: Optional[float] = None,
    ) -> Optional[OrderInfo]:
        if self._mode not in ("real_manual", "real_auto_limited"):
            raise RuntimeError(
                f"Trading not allowed in mode '{self._mode}'. "
                f"Set mode to 'real_manual' or 'real_auto_limited'"
            )

        if self._config.kill_switch:
            raise RuntimeError("Kill switch is active — trading blocked")

        params: dict[str, Any] = {
            "symbol": symbol.upper(),
            "side": side.upper(),
            "type": order_type.upper(),
            "quantity": quantity,
        }

        if order_type.upper() == "LIMIT" and price is not None:
            params["price"] = price
            params["timeInForce"] = "GTC"

        result = self._signed_post("/api/v3/order", params)
        return self._parse_order(result)

    def _signed_get(self, endpoint: str, params: dict | None = None) -> dict:
        params = dict(params or {})
        params["timestamp"] = int(time.time() * 1000)
        params["signature"] = self._sign(params)
        return self._request("GET", endpoint, params=params)

    def _signed_post(self, endpoint: str, params: dict | None = None) -> dict:
        params = dict(params or {})
        params["timestamp"] = int(time.time() * 1000)
        params["signature"] = self._sign(params)
        return self._request("POST", endpoint, data=params)

    def _public_get(self, endpoint: str) -> dict:
        return self._request("GET", endpoint)

    def _request(self, method: str, endpoint: str, **kwargs) -> dict:
        url = f"{self._base_url}{endpoint}"
        for attempt in range(self._config.binance.max_retries + 1):
            try:
                resp = self._session.request(
                    method, url,
                    timeout=self._config.binance.request_timeout_seconds,
                    **kwargs,
                )
                resp.raise_for_status()
                return resp.json()
            except requests.RequestException as e:
                if attempt < self._config.binance.max_retries:
                    time.sleep(self._config.binance.retry_delay_seconds * (attempt + 1))
                    continue
                raise RuntimeError(f"Binance API error: {e}") from e
        raise RuntimeError("Request failed")

    def _sign(self, params: dict) -> str:
        query = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
        return hmac.new(
            self._api_secret.encode("utf-8"),
            query.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def _parse_order(self, data: dict) -> OrderInfo:
        return OrderInfo(
            symbol=data.get("symbol", ""),
            order_id=int(data.get("orderId", 0)),
            side=data.get("side", ""),
            type=data.get("type", ""),
            price=float(data.get("price", 0)),
            orig_qty=float(data.get("origQty", 0)),
            executed_qty=float(data.get("executedQty", 0)),
            status=data.get("status", ""),
            time=datetime.fromtimestamp(
                data.get("time", 0) / 1000,
                tz=timezone.utc,
            ),
        )
