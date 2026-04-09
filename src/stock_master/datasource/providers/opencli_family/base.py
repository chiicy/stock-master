from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

from stock_master.common.symbols import (
    QUERY_KIND_NATURAL_LANGUAGE,
    QUERY_KIND_THEME,
    classify_query_input,
    normalize_symbol,
)

from ...interface import ProviderPayload, ProviderResult
from ...schema import ensure_payload_contract, ensure_record_contract
from ..base import BaseProvider

OPENCLI_PROVIDER_NAMES = [
    "opencli-dc",
    "opencli-xq",
    "opencli-xueqiu",
    "opencli-sinafinance",
    "opencli-bloomberg",
    "opencli-yahoo-finance",
    "opencli-iwc",
]


class OpenCliFamilyProvider(BaseProvider):
    def _first_value(self, row: ProviderPayload, *keys: str) -> Any:
        for key in keys:
            value = row.get(key)
            if value not in (None, ""):
                return value
        return None

    def _coerce_number(self, value: Any) -> int | float | None:
        if value in (None, "") or isinstance(value, bool):
            return None
        if isinstance(value, (int, float)):
            return value
        text = str(value).strip().replace(",", "")
        if not text:
            return None
        multiplier = 1.0
        if text.endswith("%"):
            text = text[:-1].strip()
        elif text.endswith("亿"):
            text = text[:-1].strip()
            multiplier = 1e8
        elif text.endswith("万"):
            text = text[:-1].strip()
            multiplier = 1e4
        match = re.search(r"-?\d+(?:\.\d+)?", text)
        if match is None:
            return None
        number = float(match.group()) * multiplier
        if number.is_integer():
            return int(number)
        return number

    def _normalize_time_value(self, value: Any) -> str | None:
        if value in (None, ""):
            return None
        if isinstance(value, (int, float)):
            timestamp = float(value)
            if timestamp > 1e12:
                timestamp /= 1000
            if timestamp > 1e9:
                return datetime.fromtimestamp(timestamp, tz=UTC).strftime("%Y-%m-%d %H:%M:%S")
            return str(value)
        text = str(value).strip()
        if text.isdigit():
            return self._normalize_time_value(int(text))
        return text

    def _normalize_symbol_value(self, row: ProviderPayload, fallback: str | None = None) -> str | None:
        symbol = self._first_str(row, "symbol")
        if symbol:
            return normalize_symbol(symbol)

        code = self._first_str(row, "code")
        exchange = self._first_str(row, "exchange")
        if code and exchange:
            upper_exchange = exchange.upper()
            if upper_exchange in {"SH", "SZ", "BJ"}:
                return normalize_symbol(f"{upper_exchange}{code}")
            if upper_exchange == "HK":
                return f"{code}.HK"

        secid = self._first_str(row, "secid")
        if secid and "." in secid:
            market_code, sec_code = secid.split(".", 1)
            market_map = {"1": "SH", "0": "SZ", "2": "BJ", "116": "HK"}
            market = market_map.get(market_code)
            if market in {"SH", "SZ", "BJ"}:
                return normalize_symbol(f"{market}{sec_code}")
            if market == "HK":
                return f"{sec_code}.HK"

        if code:
            return normalize_symbol(code)
        if fallback:
            return normalize_symbol(fallback)
        return None

    def _normalize_search_payload(self, payload: ProviderPayload, *, query: str, source_channel: str) -> ProviderResult:
        rows = payload.get("items") if isinstance(payload, dict) else None
        if not isinstance(rows, list):
            rows = [payload] if isinstance(payload, dict) else []
        items = [self._normalize_search_item(row, query=query, source_channel=source_channel) for row in rows if isinstance(row, dict)]
        if not items:
            return False
        normalized = dict(payload) if isinstance(payload, dict) else {}
        normalized["query"] = query
        normalized["items"] = items
        normalized.setdefault("status", "ok")
        normalized["source_channel"] = source_channel
        return ensure_payload_contract(
            normalized,
            capability="search",
            query=query,
            source_channel=source_channel,
        )

    def _normalize_search_item(self, row: ProviderPayload, *, query: str, source_channel: str) -> ProviderPayload:
        normalized = dict(row)
        # Search providers disagree heavily on identifier fields, so we resolve
        # `symbol/code/name/url` first and only then backfill Chinese aliases.
        symbol = self._normalize_symbol_value(row)
        code = self._first_str(row, "code")
        name = self._first_str(row, "name", "title", "text")
        price = self._coerce_number(self._first_value(row, "price", "current", "latestPrice", "regularMarketPrice"))
        percent = self._coerce_number(self._first_value(row, "percent", "changePercent"))
        url = self._first_str(row, "url", "link", "href")
        if symbol:
            normalized["symbol"] = symbol
            normalized.setdefault("代码", code or symbol[-6:])
        if code:
            normalized["code"] = code
        if name:
            normalized["name"] = name
            normalized.setdefault("名称", name)
            normalized.setdefault("title", name)
        if price is not None:
            normalized["price"] = price
        if percent is not None:
            normalized["percent"] = percent
        if url:
            normalized.setdefault("url", url)
        normalized["query"] = query
        normalized["source_channel"] = source_channel
        normalized["kind"] = "search_result"
        return ensure_record_contract(
            normalized,
            capability="search",
            kind="search_result",
            symbol=symbol,
            source_channel=source_channel,
            include_raw=True,
        )

    def _normalize_quote_payload(self, payload: ProviderPayload, *, symbol: str, source_channel: str) -> ProviderResult:
        root = dict(payload)
        row: ProviderPayload = root
        items = root.get("items")
        if isinstance(items, list):
            first_row = next((item for item in items if isinstance(item, dict)), None)
            if first_row is not None:
                row = dict(first_row)
        normalized = dict(root)
        if row is not root:
            normalized.pop("items", None)
            normalized.update(row)
        normalized_symbol = self._normalize_symbol_value(normalized, fallback=symbol)
        code = self._first_str(normalized, "code")
        name = self._first_str(normalized, "name", "company", "title")
        price = self._coerce_number(self._first_value(normalized, "price", "current", "current_price", "latestPrice", "regularMarketPrice", "trade", "last_price"))
        percent = self._coerce_number(self._first_value(normalized, "percent", "changePercent", "涨跌幅"))
        change = self._coerce_number(self._first_value(normalized, "change", "changeAmount", "涨跌额"))
        open_price = self._coerce_number(self._first_value(normalized, "open", "开盘"))
        high = self._coerce_number(self._first_value(normalized, "high", "最高"))
        low = self._coerce_number(self._first_value(normalized, "low", "最低"))
        prev_close = self._coerce_number(self._first_value(normalized, "prevClose", "昨收", "previousClose"))
        volume = self._coerce_number(self._first_value(normalized, "volume", "成交量", "vol"))
        amount = self._coerce_number(self._first_value(normalized, "amount", "成交额"))
        turnover_rate = self._coerce_number(self._first_value(normalized, "turnoverRate", "turnoverrate", "换手率"))
        market_cap = self._coerce_number(self._first_value(normalized, "marketCap", "market_capital", "总市值", "市值"))
        float_market_cap = self._coerce_number(self._first_value(normalized, "floatMarketCap", "float_market_cap", "流通市值"))
        quote_time = self._normalize_time_value(self._first_value(normalized, "timestamp", "time", "datetime", "date", "updated_at"))

        # Quote fields intentionally collapse vendor-specific names into one
        # canonical shape first; the Chinese aliases are kept for backward
        # compatibility with existing analysis/report code.
        if normalized_symbol:
            normalized["symbol"] = normalized_symbol
            normalized.setdefault("代码", code or normalized_symbol[-6:])
        if code:
            normalized["code"] = code
        if name:
            normalized["name"] = name
            normalized.setdefault("名称", name)
        if price is not None:
            normalized["price"] = price
            normalized.setdefault("current", price)
            normalized.setdefault("current_price", price)
            normalized.setdefault("latestPrice", price)
            normalized.setdefault("regularMarketPrice", price)
            normalized.setdefault("trade", price)
            normalized.setdefault("last_price", price)
            normalized.setdefault("close", price)
            normalized.setdefault("最新价", price)
        if percent is not None:
            normalized["percent"] = percent
            normalized.setdefault("涨跌幅", percent)
        if change is not None:
            normalized["change"] = change
            normalized.setdefault("changeAmount", change)
            normalized.setdefault("涨跌额", change)
        if open_price is not None:
            normalized["open"] = open_price
            normalized.setdefault("开盘", open_price)
        if high is not None:
            normalized["high"] = high
            normalized.setdefault("最高", high)
        if low is not None:
            normalized["low"] = low
            normalized.setdefault("最低", low)
        if prev_close is not None:
            normalized["prevClose"] = prev_close
            normalized.setdefault("昨收", prev_close)
        if volume is not None:
            normalized["volume"] = volume
            normalized.setdefault("成交量", volume)
        if amount is not None:
            normalized["amount"] = amount
            normalized.setdefault("成交额", amount)
        if turnover_rate is not None:
            normalized["turnoverRate"] = turnover_rate
            normalized.setdefault("换手率", turnover_rate)
        if market_cap is not None:
            normalized.setdefault("market_cap", market_cap)
            normalized.setdefault("市值", market_cap)
        if float_market_cap is not None:
            normalized.setdefault("float_market_cap", float_market_cap)
            normalized.setdefault("流通市值", float_market_cap)
        if quote_time:
            normalized.setdefault("quote_time", quote_time)
            normalized.setdefault("时间", quote_time)
        normalized["source_channel"] = source_channel
        return ensure_payload_contract(
            normalized,
            capability="quote",
            symbol=symbol,
            source_channel=source_channel,
            include_raw=True,
        )

    def _normalize_kline_payload(self, payload: ProviderPayload, *, symbol: str, source_channel: str) -> ProviderResult:
        rows = payload.get("items") if isinstance(payload, dict) else None
        if not isinstance(rows, list):
            rows = [payload] if isinstance(payload, dict) else []
        items = [self._normalize_kline_item(row, symbol=symbol) for row in rows if isinstance(row, dict)]
        if not items:
            return False
        normalized = dict(payload) if isinstance(payload, dict) else {}
        normalized["symbol"] = normalize_symbol(symbol)
        normalized["items"] = items
        normalized.setdefault("status", "ok")
        normalized["source_channel"] = source_channel
        return ensure_payload_contract(
            normalized,
            capability="kline",
            symbol=symbol,
            source_channel=source_channel,
        )

    def _normalize_kline_item(self, row: ProviderPayload, *, symbol: str) -> ProviderPayload:
        normalized = dict(row)
        # Kline rows are normalized into the canonical OHLCV vocabulary used by
        # indicators and summaries, regardless of the upstream adapter naming.
        normalized_symbol = self._normalize_symbol_value(row, fallback=symbol)
        trade_date = self._normalize_time_value(self._first_value(row, "date", "time", "datetime", "timestamp"))
        open_price = self._coerce_number(self._first_value(row, "open", "开盘"))
        high = self._coerce_number(self._first_value(row, "high", "最高"))
        low = self._coerce_number(self._first_value(row, "low", "最低"))
        close = self._coerce_number(self._first_value(row, "close", "收盘", "price", "最新价"))
        volume = self._coerce_number(self._first_value(row, "volume", "成交量", "vol"))
        amount = self._coerce_number(self._first_value(row, "amount", "成交额"))
        percent = self._coerce_number(self._first_value(row, "percent", "changePercent", "涨跌幅"))
        turnover_rate = self._coerce_number(self._first_value(row, "turnoverRate", "turnoverrate", "换手率"))

        if normalized_symbol:
            normalized["symbol"] = normalized_symbol
        if trade_date:
            normalized["date"] = trade_date
            normalized.setdefault("日期", trade_date)
        if open_price is not None:
            normalized["open"] = open_price
            normalized.setdefault("开盘", open_price)
        if high is not None:
            normalized["high"] = high
            normalized.setdefault("最高", high)
        if low is not None:
            normalized["low"] = low
            normalized.setdefault("最低", low)
        if close is not None:
            normalized["close"] = close
            normalized.setdefault("收盘", close)
        if volume is not None:
            normalized["volume"] = volume
            normalized.setdefault("成交量", volume)
        if amount is not None:
            normalized["amount"] = amount
            normalized.setdefault("成交额", amount)
        if percent is not None:
            normalized["percent"] = percent
            normalized.setdefault("涨跌幅", percent)
        if turnover_rate is not None:
            normalized["turnoverRate"] = turnover_rate
            normalized.setdefault("换手率", turnover_rate)
        return ensure_record_contract(
            normalized,
            capability="kline",
            kind="kline",
            symbol=normalized_symbol or symbol,
            include_raw=True,
        )

    def _fetch_standardized_items(
        self,
        parts: tuple[str, ...],
        *,
        capability: str,
        source_channel: str,
        kind: str,
    ) -> list[dict[str, Any]]:
        result = self._opencli_json(*parts, wrap_items=True)
        if result is False:
            return []
        rows = result.get("items") or []
        if isinstance(result, dict) and not rows:
            rows = [result]
        return [
            self._normalize_item(row, capability=capability, source_channel=source_channel, kind=kind)
            for row in rows
            if isinstance(row, dict)
        ]

    def _normalize_item(
        self,
        row: ProviderPayload,
        *,
        capability: str,
        source_channel: str,
        kind: str,
        default_title: str | None = None,
    ) -> ProviderPayload:
        # News / research / announcement records share the same common envelope:
        # `title/content/date/url/author`, while `kind` captures the semantic
        # role of the item inside stock-master.
        content = self._first_str(row, "content", "text", "summary", "description", "body")
        title = self._first_str(
            row,
            "title",
            "text",
            "content",
            "report_name",
            "name",
            "question",
            "company",
            default=default_title or "",
        )
        item_date = self._normalize_time_value(
            self._first_value(
                row,
                "date",
                "time",
                "datetime",
                "created_at",
                "published_at",
                "publish_time",
                "pub_time",
                "ctime",
                "earnings_date",
                "timestamp",
            )
        )
        url = self._first_str(row, "url", "link", "href")
        author = self._first_str(row, "author", "org", "机构", "机构名称", "media", "source")
        rating = self._first_str(row, "rating", "评级", "东财评级")
        normalized = dict(row)
        normalized.setdefault("title", title)
        normalized.setdefault("date", item_date)
        normalized.setdefault("publish_time", item_date)
        normalized.setdefault("url", url)
        normalized.setdefault("标题", title)
        normalized.setdefault("发布时间", item_date)
        normalized.setdefault("时间", item_date)
        normalized.setdefault("链接", url)
        if content:
            normalized.setdefault("content", content)
            normalized.setdefault("summary", content)
            normalized.setdefault("摘要", content)
        if author:
            normalized.setdefault("author", author)
        normalized["source_channel"] = source_channel
        normalized["kind"] = kind
        if kind in {"news", "news_flash", "market_news", "commentary"}:
            normalized.setdefault("新闻标题", title)
            normalized.setdefault("新闻内容", content or title)
        if kind in {"research", "earnings_date"}:
            normalized.setdefault("报告名称", title)
            if author:
                normalized.setdefault("机构", author)
        if rating:
            normalized.setdefault("评级", rating)
            normalized.setdefault("东财评级", rating)
        if kind in {"announcement", "announcement_commentary"}:
            normalized.setdefault("公告标题", title)
            normalized.setdefault("公告时间", item_date)
        return ensure_record_contract(
            normalized,
            capability=capability,
            kind=kind,
            source_channel=source_channel,
            include_raw=True,
        )

    def _first_str(self, row: ProviderPayload, *keys: str, default: str | None = None) -> str | None:
        for key in keys:
            value = row.get(key)
            if value not in (None, ""):
                return str(value)
        return default

    def _looks_like_question(self, query: str) -> bool:
        query_kind = classify_query_input(query)["kind"]
        return query_kind in {QUERY_KIND_NATURAL_LANGUAGE, QUERY_KIND_THEME}

    def _is_a_share_symbol(self, symbol: str) -> bool:
        normalized = normalize_symbol(symbol)
        return normalized.startswith(("SH", "SZ", "BJ"))
