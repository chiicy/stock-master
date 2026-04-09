from __future__ import annotations

from ...interface import ProviderResult
from ...schema import ensure_payload_contract
from .base import OpenCliFamilyProvider


class OpenCliIwcProvider(OpenCliFamilyProvider):
    def __init__(self, backend, available: bool) -> None:
        super().__init__("opencli-iwc", backend, available)

    def get_search(self, query: str) -> ProviderResult:
        if not self._looks_like_question(query):
            return False
        iwc = self._opencli_json("iwc", "query", "--question", query)
        if iwc is False:
            return False
        return ensure_payload_contract(
            {
                "query": query,
                "items": [
                    self._normalize_item(
                        iwc,
                        capability="search",
                        source_channel="iwc.query",
                        kind="qa",
                        default_title=query,
                    )
                ],
            },
            capability="search",
            query=query,
            source_channel="iwc.query",
        )
