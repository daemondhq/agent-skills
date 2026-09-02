"""Atlas Cloud image provider for the nano-banana-all skill."""

from __future__ import annotations

import mimetypes
import time
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests

API_BASE_URL = "https://api.atlascloud.ai"
CATALOG_URL = f"{API_BASE_URL}/api/v1/models"
UPLOAD_URL = f"{API_BASE_URL}/api/v1/model/uploadMedia"
TEXT_MODEL = "google/nano-banana-2/text-to-image"
EDIT_MODEL = "google/nano-banana-2/edit"
TRANSIENT_STATUS_CODES = {408, 429, 500, 502, 503, 504}
SUCCESS_STATUSES = {"completed", "succeeded"}
FAILURE_STATUSES = {"failed", "canceled", "cancelled"}


def _unwrap(payload: Any) -> Any:
    if isinstance(payload, dict) and isinstance(payload.get("data"), (dict, list)):
        return payload["data"]
    return payload


class AtlasImageProvider:
    """Generate or edit one image through Atlas Cloud."""

    def __init__(self, api_key: str, *, http: Any = requests, sleep: Any = time.sleep):
        if not api_key:
            raise ValueError("ATLASCLOUD_API_KEY is required for the Atlas provider")
        self.api_key = api_key
        self.http = http
        self.sleep = sleep

    @property
    def headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
            "User-Agent": "daemond-agent-skills-nano-banana/1.0",
        }

    def _discover(self, model: str, timeout: float) -> tuple[str, str, dict[str, Any]]:
        public_headers = {
            "Accept": "application/json",
            "User-Agent": self.headers["User-Agent"],
        }
        response = self.http.get(CATALOG_URL, headers=public_headers, timeout=timeout)
        response.raise_for_status()
        catalog = _unwrap(response.json())
        model_info = next(
            (item for item in catalog if item.get("model") == model), None
        )
        if not model_info:
            raise ValueError(f"Atlas Cloud model is not available: {model}")

        response = self.http.get(
            model_info["schema"], headers=public_headers, timeout=timeout
        )
        response.raise_for_status()
        schema = response.json()
        run_path = None
        result_path = None
        for path, operations in schema.get("paths", {}).items():
            if operations.get("x-api-name") == "model_run":
                run_path = path
            elif operations.get("x-api-name") == "model_result":
                result_path = path
        if not run_path or not result_path:
            raise ValueError("Atlas schema is missing model_run or model_result")
        return run_path, result_path, schema

    @staticmethod
    def _validate(schema: dict[str, Any], payload: dict[str, Any]) -> None:
        input_schema = schema.get("components", {}).get("schemas", {}).get("Input", {})
        properties = input_schema.get("properties", {})
        unsupported = sorted(set(payload) - set(properties))
        if unsupported:
            raise ValueError(
                f"Unsupported Atlas input fields: {', '.join(unsupported)}"
            )
        missing = [
            field for field in input_schema.get("required", []) if field not in payload
        ]
        if missing:
            raise ValueError(f"Missing Atlas input fields: {', '.join(missing)}")
        for field, value in payload.items():
            choices = properties.get(field, {}).get("enum")
            if choices and value not in choices:
                raise ValueError(
                    f"Invalid {field!r}; expected one of: {', '.join(choices)}"
                )

    def _upload(self, input_image: Path, timeout: float) -> str:
        content_type = (
            mimetypes.guess_type(input_image.name)[0] or "application/octet-stream"
        )
        with input_image.open("rb") as image_file:
            response = self.http.post(
                UPLOAD_URL,
                headers=self.headers,
                files={"file": (input_image.name, image_file, content_type)},
                timeout=timeout,
            )
        response.raise_for_status()
        upload = _unwrap(response.json())
        image_url = upload.get("download_url") or upload.get("url")
        if not isinstance(image_url, str) or not image_url.startswith("https://"):
            raise RuntimeError("Atlas Cloud upload did not return an HTTPS image URL")
        return image_url

    def _poll(
        self,
        url: str,
        *,
        poll_interval: float,
        max_polls: int,
        timeout: float,
    ) -> dict[str, Any]:
        for attempt in range(max_polls):
            response = None
            try:
                response = self.http.get(url, headers=self.headers, timeout=timeout)
                if response.status_code in TRANSIENT_STATUS_CODES:
                    raise requests.HTTPError(f"Transient HTTP {response.status_code}")
                response.raise_for_status()
                prediction = _unwrap(response.json())
            except requests.HTTPError:
                if (
                    response is None
                    or response.status_code not in TRANSIENT_STATUS_CODES
                ):
                    raise
                if attempt + 1 >= max_polls:
                    raise
                self.sleep(min(poll_interval * (2**attempt), 10.0))
                continue
            except (requests.ConnectionError, requests.Timeout):
                if attempt + 1 >= max_polls:
                    raise
                self.sleep(min(poll_interval * (2**attempt), 10.0))
                continue

            status = str(prediction.get("status") or "").lower()
            if status in SUCCESS_STATUSES:
                return prediction
            if status in FAILURE_STATUSES:
                detail = prediction.get("error") or prediction.get("message") or status
                raise RuntimeError(f"Atlas Cloud generation failed: {detail}")
            if attempt + 1 < max_polls:
                self.sleep(min(poll_interval * (2**attempt), 10.0))

        raise TimeoutError(f"Atlas prediction did not complete after {max_polls} polls")

    def generate(
        self,
        prompt: str,
        *,
        input_image: Path | None = None,
        resolution: str = "1K",
        poll_interval: float = 2.0,
        max_polls: int = 60,
        timeout: float = 60,
    ) -> bytes:
        """Make one generation submission and return the resulting image bytes."""
        model = EDIT_MODEL if input_image else TEXT_MODEL
        run_path, result_path, schema = self._discover(model, timeout)
        payload: dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "resolution": resolution.lower(),
            "output_format": "png",
        }
        if input_image:
            payload["images"] = [self._upload(input_image, timeout)]
        self._validate(schema, payload)

        # Generation may be billable, so this POST is intentionally never retried.
        response = self.http.post(
            f"{API_BASE_URL}{run_path}",
            headers={**self.headers, "Content-Type": "application/json"},
            json=payload,
            timeout=timeout,
        )
        response.raise_for_status()
        prediction = _unwrap(response.json())
        prediction_id = prediction.get("id")
        if not prediction_id:
            raise RuntimeError("Atlas Cloud response did not include a prediction id")

        if str(prediction.get("status") or "").lower() not in SUCCESS_STATUSES:
            encoded_id = quote(str(prediction_id), safe="")
            result_path = result_path.replace("{request_id}", encoded_id)
            result_url = f"{API_BASE_URL}{result_path}"
            prediction = self._poll(
                result_url,
                poll_interval=poll_interval,
                max_polls=max_polls,
                timeout=timeout,
            )

        outputs = prediction.get("outputs") or []
        if (
            not outputs
            or not isinstance(outputs[0], str)
            or not outputs[0].startswith("https://")
        ):
            raise RuntimeError("Atlas Cloud completed without an HTTPS image output")
        response = self.http.get(outputs[0], timeout=timeout)
        response.raise_for_status()
        image = response.content
        is_png = image.startswith(b"\x89PNG\r\n\x1a\n")
        is_jpeg = image.startswith(b"\xff\xd8\xff")
        is_webp = image.startswith(b"RIFF") and image[8:12] == b"WEBP"
        if not image or not (is_png or is_jpeg or is_webp):
            raise RuntimeError("Atlas Cloud returned an unsupported image payload")
        return image
