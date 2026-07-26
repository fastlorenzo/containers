"""Async client for the Open WebUI v1 API.

Covers the four surfaces the bridge needs: knowledge collections, the file
store, retrieval, and chat export. Every call fails loudly — a bridge that
silently degrades to "no results" is indistinguishable from an empty vault,
and Open WebUI has changed this API under us before (open-webui#14432).
"""

import asyncio
import logging
from typing import Any

import httpx

LOG = logging.getLogger("obsidian-bridge.webui")

# Endpoints whose exact shape is confirmed against the running instance's
# /docs. The chat listing has moved between releases, so it is probed.
_CHAT_LIST_CANDIDATES = ("/api/v1/chats/list", "/api/v1/chats/")


class WebUIError(RuntimeError):
    pass


class WebUIClient:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        *,
        max_retries: int = 5,
        timeout: float = 120.0,
    ) -> None:
        self._base = base_url.rstrip("/")
        self._max_retries = max_retries
        self._client = httpx.AsyncClient(
            base_url=self._base,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=timeout,
        )
        self._chat_list_path: str | None = None

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        """Issue a request, retrying only what is worth retrying.

        429 and 5xx are transient (the gateway key is rate limited at rpm 120,
        and llama-swap may be mid model-swap). 4xx otherwise is a contract
        problem and retrying just delays the error.
        """
        delay = 1.0
        last_exc: Exception | None = None

        for attempt in range(1, self._max_retries + 1):
            try:
                response = await self._client.request(method, path, **kwargs)
            except httpx.RequestError as exc:
                last_exc = exc
                if attempt == self._max_retries:
                    break
                LOG.warning("%s %s failed (%s), retry %d", method, path, exc, attempt)
            else:
                if response.status_code < 400:
                    return response
                if response.status_code == 429 or response.status_code >= 500:
                    if attempt == self._max_retries:
                        raise WebUIError(
                            f"{method} {path} -> {response.status_code} after "
                            f"{attempt} attempts: {response.text[:300]}"
                        )
                    retry_after = response.headers.get("retry-after")
                    wait = float(retry_after) if retry_after and retry_after.isdigit() else delay
                    LOG.warning(
                        "%s %s -> %d, backing off %.1fs", method, path, response.status_code, wait
                    )
                    await asyncio.sleep(wait)
                    delay = min(delay * 2, 30.0)
                    continue
                raise WebUIError(
                    f"{method} {path} -> {response.status_code}: {response.text[:300]}"
                )

            await asyncio.sleep(delay)
            delay = min(delay * 2, 30.0)

        raise WebUIError(f"{method} {path} failed after {self._max_retries} attempts: {last_exc}")

    # -- knowledge collections ---------------------------------------------

    async def list_knowledge(self) -> list[dict[str, Any]]:
        response = await self._request("GET", "/api/v1/knowledge/")
        payload = response.json()
        return payload if isinstance(payload, list) else []

    async def ensure_collection(self, name: str, description: str) -> str:
        """Return the knowledge id for `name`, creating the collection if absent."""
        for entry in await self.list_knowledge():
            if entry.get("name") == name:
                return str(entry["id"])

        response = await self._request(
            "POST",
            "/api/v1/knowledge/create",
            json={"name": name, "description": description},
        )
        kid = str(response.json()["id"])
        LOG.info("created collection %r (%s)", name, kid)
        return kid

    async def upload_file(self, filename: str, content: bytes) -> str:
        response = await self._request(
            "POST",
            "/api/v1/files/",
            files={"file": (filename, content, "text/markdown")},
        )
        return str(response.json()["id"])

    async def add_file_to_collection(self, kid: str, file_id: str) -> None:
        await self._request(
            "POST", f"/api/v1/knowledge/{kid}/file/add", json={"file_id": file_id}
        )

    async def remove_file_from_collection(self, kid: str, file_id: str) -> None:
        """Detach a file from a collection, tolerating an already-absent file."""
        try:
            await self._request(
                "POST", f"/api/v1/knowledge/{kid}/file/remove", json={"file_id": file_id}
            )
        except WebUIError as exc:
            LOG.warning("remove %s from %s: %s", file_id, kid, exc)

    async def delete_file(self, file_id: str) -> None:
        try:
            await self._request("DELETE", f"/api/v1/files/{file_id}")
        except WebUIError as exc:
            LOG.warning("delete file %s: %s", file_id, exc)

    # -- retrieval ---------------------------------------------------------

    async def query_collection(
        self,
        kid: str,
        query: str,
        *,
        k: int = 16,
        k_reranker: int = 6,
        r: float = 0.0,
        hybrid: bool = True,
    ) -> dict[str, Any]:
        response = await self._request(
            "POST",
            "/api/v1/retrieval/query/collection",
            json={
                "collection_names": [kid],
                "query": query,
                "k": k,
                "k_reranker": k_reranker,
                "r": r,
                "hybrid": hybrid,
            },
        )
        return response.json()

    # -- chats -------------------------------------------------------------

    async def list_chats(self) -> list[dict[str, Any]]:
        """List the key owner's chats, probing for the endpoint this release uses."""
        paths = (
            [self._chat_list_path] if self._chat_list_path else list(_CHAT_LIST_CANDIDATES)
        )
        for path in paths:
            assert path is not None
            try:
                response = await self._request("GET", path)
            except WebUIError as exc:
                LOG.debug("chat listing %s unavailable: %s", path, exc)
                continue
            payload = response.json()
            if isinstance(payload, dict):
                payload = payload.get("chats", payload.get("data", []))
            if isinstance(payload, list):
                self._chat_list_path = path
                return payload

        raise WebUIError(
            "no usable chat listing endpoint; check /docs on the instance and set the path"
        )

    async def get_chat(self, chat_id: str) -> dict[str, Any]:
        response = await self._request("GET", f"/api/v1/chats/{chat_id}")
        payload = response.json()
        return payload if isinstance(payload, dict) else {}
