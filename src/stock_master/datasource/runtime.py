#!/usr/bin/env python3
from __future__ import annotations

import json
import threading
from datetime import UTC, datetime
from typing import Any, Sequence

from .interface import CapabilitySpec, ProviderPayload, ProviderResult, StockDataProvider, get_capability_spec
from .schema import action_to_capability, ensure_payload_contract


def is_provider_success(data: ProviderResult) -> bool:
    if data is False:
        return False
    if not isinstance(data, dict):
        return False
    if data.get('error'):
        return False
    if data.get('status') in {'error', 'empty'}:
        return False
    return True


def tag_payload(payload: ProviderPayload, source: str, fallback_path: list[str], capability: str) -> ProviderPayload:
    tagged = dict(payload)
    existing_source = tagged.get('source')
    if existing_source and existing_source != source:
        tagged.setdefault('source_detail', existing_source)
    tagged['source'] = source
    tagged['fallback_path'] = fallback_path
    return ensure_payload_contract(tagged, capability=action_to_capability(capability))


def _record_identity(record: Any) -> str:
    try:
        return json.dumps(record, sort_keys=True, ensure_ascii=False, default=str)
    except TypeError:
        return repr(record)


def _dedupe_records(records: list[Any], spec: CapabilitySpec) -> list[Any]:
    seen: set[str] = set()
    deduped: list[Any] = []
    for record in records:
        key = _record_identity(record)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(record)
    return deduped


def _has_sufficient_fields(payload: ProviderPayload, spec: CapabilitySpec) -> bool:
    if not spec.sufficient_fields:
        return True
    for group in spec.sufficient_fields:
        if any(payload.get(field) not in (None, '', [], {}) for field in group):
            continue
        return False
    return True


def _sort_records(records: list[Any], spec: CapabilitySpec) -> list[Any]:
    if spec.sort_by != 'date_desc':
        return records

    min_dt = datetime.min.replace(tzinfo=UTC)

    def normalize_dt(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    def extract_date(record: Any) -> tuple[int, datetime]:
        if not isinstance(record, dict):
            return (0, min_dt)
        raw = record.get('date') or record.get('time') or record.get('datetime') or record.get('created_at') or record.get('published_at')
        if raw in (None, ''):
            return (0, min_dt)
        text = str(raw).strip().replace('Z', '+00:00')
        for candidate in (text, text.replace('/', '-')):
            try:
                return (1, normalize_dt(datetime.fromisoformat(candidate)))
            except ValueError:
                continue
        for fmt in ('%Y-%m-%d %H:%M', '%Y-%m-%d', '%Y%m%d'):
            try:
                return (1, normalize_dt(datetime.strptime(text, fmt)))
            except ValueError:
                continue
        return (0, min_dt)

    return sorted(records, key=extract_date, reverse=True)


def aggregate_payloads(
    payloads: Sequence[ProviderPayload],
    sources: list[str],
    fallback_path: list[str],
    spec: CapabilitySpec,
    capability: str,
) -> ProviderPayload:
    merged: ProviderPayload = {
        'status': 'ok',
        'source': 'merged',
        'sources': sources,
        'fallback_path': fallback_path,
    }
    list_keys = spec.merge_keys or ('items', 'rows')
    for payload in payloads:
        for key, value in payload.items():
            if key in {'source', 'source_detail', 'fallback_path'}:
                continue
            if key in list_keys and isinstance(value, list):
                merged.setdefault(key, [])
                merged[key].extend(value)
                continue
            merged.setdefault(key, value)
    for key in list_keys:
        if key in merged and isinstance(merged[key], list):
            merged[key] = _sort_records(_dedupe_records(merged[key], spec), spec)
    return ensure_payload_contract(merged, capability=action_to_capability(capability))


class ProviderRouter:
    def __init__(self, providers: Sequence[StockDataProvider], per_provider_timeout: float = 15) -> None:
        self.providers = list(providers)
        self.per_provider_timeout = per_provider_timeout

    def _resolve_providers(self, providers: Sequence[StockDataProvider] | None = None) -> list[StockDataProvider]:
        return list(providers or self.providers)

    def _invoke_with_timeout(self, provider: StockDataProvider, capability: str, *args: Any) -> ProviderResult:
        result: dict[str, Any] = {'value': False}

        def worker() -> None:
            try:
                handler = getattr(provider, capability)
                result['value'] = handler(*args)
            except Exception:
                result['value'] = False

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        thread.join(timeout=self.per_provider_timeout)
        if thread.is_alive():
            return False
        return result.get('value', False)

    def dispatch(
        self,
        capability: str,
        *args: Any,
        spec: CapabilitySpec | None = None,
        strategy: str | None = None,
        providers: Sequence[StockDataProvider] | None = None,
        routing_hint: dict[str, Any] | None = None,
    ) -> ProviderPayload:
        capability_spec = spec or get_capability_spec(capability)
        if strategy in {'merge', 'aggregate'}:
            capability_spec = CapabilitySpec(
                strategy='aggregate',
                merge_keys=capability_spec.merge_keys,
                dedupe_by=capability_spec.dedupe_by,
                sort_by=capability_spec.sort_by,
                sufficient_fields=capability_spec.sufficient_fields,
            )
        elif strategy == 'first_success':
            capability_spec = CapabilitySpec(
                strategy='first_success',
                merge_keys=capability_spec.merge_keys,
                dedupe_by=capability_spec.dedupe_by,
                sort_by=capability_spec.sort_by,
                sufficient_fields=capability_spec.sufficient_fields,
            )
        if capability_spec.strategy == 'aggregate':
            return self._dispatch_aggregate(capability, capability_spec, *args, providers=providers, routing_hint=routing_hint)
        return self._dispatch_first_success(capability, capability_spec, *args, providers=providers, routing_hint=routing_hint)

    def _dispatch_first_success(
        self,
        capability: str,
        spec: CapabilitySpec,
        *args: Any,
        providers: Sequence[StockDataProvider] | None = None,
        routing_hint: dict[str, Any] | None = None,
    ) -> ProviderPayload:
        path: list[str] = []
        for provider in self._resolve_providers(providers):
            if not provider.available:
                continue
            path.append(provider.name)
            value = self._invoke_with_timeout(provider, capability, *args)
            if is_provider_success(value) and _has_sufficient_fields(value, spec):
                tagged = tag_payload(value, provider.name, path.copy(), capability)
                if routing_hint:
                    tagged['routing_hint'] = dict(routing_hint)
                return tagged
        empty = ensure_payload_contract(
            {
                'status': 'empty',
                'fallback_path': path,
            },
            capability=action_to_capability(capability),
            status='empty',
        )
        if routing_hint:
            empty['routing_hint'] = dict(routing_hint)
        return empty

    def _dispatch_aggregate(
        self,
        capability: str,
        spec: CapabilitySpec,
        *args: Any,
        providers: Sequence[StockDataProvider] | None = None,
        routing_hint: dict[str, Any] | None = None,
    ) -> ProviderPayload:
        path: list[str] = []
        payloads: list[ProviderPayload] = []
        sources: list[str] = []
        for provider in self._resolve_providers(providers):
            if not provider.available:
                continue
            path.append(provider.name)
            value = self._invoke_with_timeout(provider, capability, *args)
            if not is_provider_success(value):
                continue
            payloads.append(value)
            sources.append(provider.name)
        if payloads:
            merged = aggregate_payloads(payloads, sources, path, spec, capability)
            if routing_hint:
                merged['routing_hint'] = dict(routing_hint)
            return merged
        empty = ensure_payload_contract(
            {
                'status': 'empty',
                'fallback_path': path,
            },
            capability=action_to_capability(capability),
            status='empty',
        )
        if routing_hint:
            empty['routing_hint'] = dict(routing_hint)
        return empty
