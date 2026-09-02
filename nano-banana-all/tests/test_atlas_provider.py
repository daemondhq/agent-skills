import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import requests

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from atlas_provider import EDIT_MODEL, TEXT_MODEL, AtlasImageProvider  # noqa: E402


def schema_for(model, *, editing=False):
    properties = {
        "model": {"type": "string"},
        "prompt": {"type": "string"},
        "resolution": {"enum": ["1k", "2k", "4k"]},
        "output_format": {"enum": ["png", "jpeg"]},
    }
    required = ["model", "prompt"]
    if editing:
        properties["images"] = {"type": "array"}
        required.append("images")
    return {
        "paths": {
            "/api/v1/model/generateImage": {"x-api-name": "model_run"},
            "/api/v1/model/prediction/{request_id}": {"x-api-name": "model_result"},
        },
        "components": {
            "schemas": {"Input": {"required": required, "properties": properties}}
        },
    }


class FakeResponse:
    def __init__(self, payload=None, *, content=b"", status_code=200):
        self.payload = payload
        self.content = content
        self.status_code = status_code

    def json(self):
        return self.payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")


class FakeHTTP:
    def __init__(self, *, gets, posts):
        self.gets = list(gets)
        self.posts = list(posts)
        self.get_calls = []
        self.post_calls = []

    def get(self, url, **kwargs):
        self.get_calls.append((url, kwargs))
        response = self.gets.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    def post(self, url, **kwargs):
        self.post_calls.append((url, kwargs))
        response = self.posts.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def discovery_gets(model, schema, *remaining):
    return [
        FakeResponse(
            {"data": [{"model": model, "schema": "https://schema.test/model.json"}]}
        ),
        FakeResponse(schema),
        *remaining,
    ]


class AtlasImageProviderTests(unittest.TestCase):
    def test_text_generation_discovers_schema_submits_once_and_downloads(self):
        http = FakeHTTP(
            gets=discovery_gets(
                TEXT_MODEL,
                schema_for(TEXT_MODEL),
                FakeResponse(
                    {
                        "data": {
                            "id": "pred-1",
                            "status": "completed",
                            "outputs": ["https://cdn.test/image.png"],
                        }
                    }
                ),
                FakeResponse(content=b"\x89PNG\r\n\x1a\npng-data"),
            ),
            posts=[FakeResponse({"data": {"id": "pred-1", "status": "processing"}})],
        )
        provider = AtlasImageProvider("atlas-test", http=http, sleep=lambda _: None)

        image = provider.generate("a diagram", resolution="2K")

        self.assertEqual(image, b"\x89PNG\r\n\x1a\npng-data")
        self.assertEqual(len(http.post_calls), 1)
        self.assertEqual(http.post_calls[0][1]["json"]["model"], TEXT_MODEL)
        self.assertEqual(http.post_calls[0][1]["json"]["resolution"], "2k")

    def test_edit_uploads_local_image_before_one_generation_submission(self):
        with tempfile.TemporaryDirectory() as directory:
            input_image = Path(directory) / "input.png"
            input_image.write_bytes(b"input")
            http = FakeHTTP(
                gets=discovery_gets(
                    EDIT_MODEL,
                    schema_for(EDIT_MODEL, editing=True),
                    FakeResponse(content=b"\xff\xd8\xffjpeg-data"),
                ),
                posts=[
                    FakeResponse(
                        {"data": {"download_url": "https://cdn.test/input.png"}}
                    ),
                    FakeResponse(
                        {
                            "data": {
                                "id": "pred-2",
                                "status": "completed",
                                "outputs": ["https://cdn.test/edit.jpg"],
                            }
                        }
                    ),
                ],
            )
            provider = AtlasImageProvider("atlas-test", http=http)

            image = provider.generate("make it blue", input_image=input_image)

        self.assertEqual(image, b"\xff\xd8\xffjpeg-data")
        self.assertEqual(len(http.post_calls), 2)
        self.assertIn("files", http.post_calls[0][1])
        self.assertEqual(
            http.post_calls[1][1]["json"]["images"], ["https://cdn.test/input.png"]
        )

    def test_generation_post_failure_is_not_retried(self):
        http = FakeHTTP(
            gets=discovery_gets(TEXT_MODEL, schema_for(TEXT_MODEL)),
            posts=[requests.ConnectionError("connection lost")],
        )
        provider = AtlasImageProvider("atlas-test", http=http)

        with self.assertRaises(requests.ConnectionError):
            provider.generate("a diagram")

        self.assertEqual(len(http.post_calls), 1)

    def test_only_transient_prediction_get_is_retried(self):
        http = FakeHTTP(
            gets=discovery_gets(
                TEXT_MODEL,
                schema_for(TEXT_MODEL),
                FakeResponse(status_code=503),
                FakeResponse(
                    {
                        "data": {
                            "id": "pred-3",
                            "status": "completed",
                            "outputs": ["https://cdn.test/image.png"],
                        }
                    }
                ),
                FakeResponse(content=b"\x89PNG\r\n\x1a\npng-data"),
            ),
            posts=[FakeResponse({"data": {"id": "pred-3", "status": "processing"}})],
        )
        sleep = mock.Mock()
        provider = AtlasImageProvider("atlas-test", http=http, sleep=sleep)

        provider.generate("a diagram")

        sleep.assert_called_once_with(2.0)
        self.assertEqual(len(http.post_calls), 1)

    def test_permanent_prediction_error_is_not_retried(self):
        http = FakeHTTP(
            gets=discovery_gets(
                TEXT_MODEL,
                schema_for(TEXT_MODEL),
                FakeResponse(status_code=401),
            ),
            posts=[FakeResponse({"data": {"id": "pred-4", "status": "processing"}})],
        )
        sleep = mock.Mock()
        provider = AtlasImageProvider("atlas-test", http=http, sleep=sleep)

        with self.assertRaises(requests.HTTPError):
            provider.generate("a diagram")

        sleep.assert_not_called()
        self.assertEqual(len(http.get_calls), 3)
        self.assertEqual(len(http.post_calls), 1)

    def test_invalid_resolution_is_rejected_before_generation_post(self):
        http = FakeHTTP(
            gets=discovery_gets(TEXT_MODEL, schema_for(TEXT_MODEL)), posts=[]
        )
        provider = AtlasImageProvider("atlas-test", http=http)

        with self.assertRaisesRegex(ValueError, "Invalid 'resolution'"):
            provider.generate("a diagram", resolution="8K")

        self.assertEqual(http.post_calls, [])


if __name__ == "__main__":
    unittest.main()
