"""Regression tests for source-grounded guidance and read-only Xquik search."""

from __future__ import annotations

import importlib.util
import io
import json
import unittest
from contextlib import redirect_stderr, redirect_stdout
from http.client import HTTPMessage
from pathlib import Path
from types import ModuleType
from urllib.error import HTTPError, URLError
from urllib.request import Request

ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / ".claude" / "skills" / "x-boost" / "scripts" / "xquik_search.py"


def load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("xquik_search", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load Xquik search helper.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


XQUIK_SEARCH = load_script()


class FakeResponse:
    def __init__(
        self,
        payload: object,
        *,
        status: int = 200,
        content_length: str | None = None,
    ) -> None:
        self.body = json.dumps(payload).encode()
        self.headers = (
            {"Content-Length": content_length} if content_length is not None else {}
        )
        self.status = status
        self.closed = False
        self.requested_amounts: list[int] = []

    def close(self) -> None:
        self.closed = True

    def read(self, amount: int = -1) -> bytes:
        self.requested_amounts.append(amount)
        return self.body if amount < 0 else self.body[:amount]


class FakeOpener:
    def __init__(self, response: FakeResponse) -> None:
        self.response = response
        self.requests: list[tuple[Request, int]] = []

    def open(self, request: Request, timeout: int) -> FakeResponse:
        self.requests.append((request, timeout))
        return self.response


class SearchTests(unittest.TestCase):
    def test_search_uses_fixed_read_only_endpoint_and_normalizes_results(self) -> None:
        response = FakeResponse(
            {
                "tweets": [
                    {
                        "id": "2030000000000000000",
                        "text": "A source post",
                        "created_at": "2026-07-30T12:00:00Z",
                        "author": {"username": "source_user", "name": "Source"},
                        "like_count": 12,
                        "reply_count": 3,
                        "retweet_count": 4,
                        "quote_count": 2,
                        "view_count": 500,
                    }
                ],
                "has_more": True,
                "next_cursor": "opaque",
            }
        )
        opener = FakeOpener(response)

        result = XQUIK_SEARCH.search(
            query="launch day",
            limit=10,
            query_type="Top",
            cursor="page-one",
            api_key="xq_test",
            opener=opener,
        )

        self.assertEqual(result["source"], "Xquik")
        self.assertIs(result["untrusted"], True)
        self.assertIs(result["has_next_page"], True)
        self.assertEqual(result["next_cursor"], "opaque")
        self.assertEqual(result["tweets"][0]["created_at"], "2026-07-30T12:00:00Z")
        self.assertEqual(result["tweets"][0]["metrics"]["likes"], 12)
        self.assertEqual(
            result["tweets"][0]["url"],
            "https://x.com/source_user/status/2030000000000000000",
        )
        request, timeout = opener.requests[0]
        self.assertEqual(request.get_method(), "GET")
        self.assertEqual(request.host, "xquik.com")
        self.assertEqual(request.selector.split("?", 1)[0], "/api/v1/x/tweets/search")
        self.assertIn("q=launch+day", request.selector)
        self.assertIn("query_type=Top", request.selector)
        self.assertIn("cursor=page-one", request.selector)
        self.assertEqual(request.get_header("X-api-key"), "xq_test")
        self.assertEqual(timeout, XQUIK_SEARCH.TIMEOUT_SECONDS)
        self.assertIs(response.closed, True)
        self.assertEqual(
            response.requested_amounts,
            [XQUIK_SEARCH.MAX_RESPONSE_BYTES + 1],
        )

    def test_search_rejects_invalid_inputs_before_network_access(self) -> None:
        opener = FakeOpener(FakeResponse({"tweets": []}))

        invalid_cases: list[tuple[str, int, str, str | None, str]] = [
            ("", 10, "Latest", None, "xq_test"),
            (
                "a" * (XQUIK_SEARCH.MAX_QUERY_LENGTH + 1),
                10,
                "Latest",
                None,
                "xq_test",
            ),
            ("test", 0, "Latest", None, "xq_test"),
            ("test", 10, "New", None, "xq_test"),
            (
                "test",
                10,
                "Latest",
                "a" * (XQUIK_SEARCH.MAX_CURSOR_LENGTH + 1),
                "xq_test",
            ),
            ("test", 10, "Latest", None, ""),
            ("test", 10, "Latest", None, "xq_bad\nheader"),
        ]
        for query, limit, query_type, cursor, api_key in invalid_cases:
            with (
                self.subTest(query=query, limit=limit, query_type=query_type),
                self.assertRaises(ValueError),
            ):
                XQUIK_SEARCH.search(
                    query=query,
                    limit=limit,
                    query_type=query_type,
                    cursor=cursor,
                    api_key=api_key,
                    opener=opener,
                )

        self.assertEqual(opener.requests, [])

    def test_search_rejects_oversized_or_malformed_responses(self) -> None:
        oversized = FakeOpener(
            FakeResponse(
                {"tweets": []},
                content_length=str(XQUIK_SEARCH.MAX_RESPONSE_BYTES + 1),
            )
        )
        with self.assertRaisesRegex(ValueError, "size limit"):
            XQUIK_SEARCH.search(
                query="test",
                limit=10,
                query_type="Latest",
                cursor=None,
                api_key="xq_test",
                opener=oversized,
            )

        malformed = FakeOpener(FakeResponse({"results": []}))
        with self.assertRaisesRegex(TypeError, "tweet list"):
            XQUIK_SEARCH.search(
                query="test",
                limit=10,
                query_type="Latest",
                cursor=None,
                api_key="xq_test",
                opener=malformed,
            )

        invalid_json_response = FakeResponse({"tweets": []})
        invalid_json_response.body = b"{"
        with self.assertRaisesRegex(ValueError, "invalid JSON"):
            XQUIK_SEARCH.search(
                query="test",
                limit=10,
                query_type="Latest",
                cursor=None,
                api_key="xq_test",
                opener=FakeOpener(invalid_json_response),
            )

        malformed_tweet = FakeOpener(FakeResponse({"tweets": [None]}))
        with self.assertRaisesRegex(TypeError, "tweet record"):
            XQUIK_SEARCH.search(
                query="test",
                limit=10,
                query_type="Latest",
                cursor=None,
                api_key="xq_test",
                opener=malformed_tweet,
            )

    def test_main_reports_safe_error_without_leaking_the_api_key(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()
        secret = "xq_do-not-print"

        with redirect_stdout(stdout), redirect_stderr(stderr):
            status = XQUIK_SEARCH.main(
                ["--query", "test"],
                environment={"XQUIK_API_KEY": secret},
                opener=FakeOpener(FakeResponse({"tweets": []}, status=503)),
            )

        self.assertEqual(status, 1)
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(
            json.loads(stderr.getvalue()),
            {"error": "Xquik returned HTTP 503."},
        )
        self.assertNotIn(secret, stderr.getvalue())

    def test_main_prints_normalized_page_and_network_errors_are_generic(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            status = XQUIK_SEARCH.main(
                ["--query", "test"],
                environment={"XQUIK_API_KEY": "xq_test"},
                opener=FakeOpener(FakeResponse({"tweets": []})),
            )

        self.assertEqual(status, 0)
        self.assertEqual(json.loads(stdout.getvalue())["tweets"], [])
        self.assertEqual(stderr.getvalue(), "")
        http_error = HTTPError(
            "https://xquik.com",
            429,
            "rate limit",
            HTTPMessage(),
            io.BytesIO(),
        )
        try:
            self.assertEqual(
                XQUIK_SEARCH._safe_error(http_error),
                "Xquik returned HTTP 429.",
            )
        finally:
            http_error.close()
        self.assertEqual(
            XQUIK_SEARCH._safe_error(URLError("offline")),
            "Could not reach Xquik.",
        )
        self.assertEqual(
            XQUIK_SEARCH._safe_error(RuntimeError("private detail")),
            "Xquik search failed.",
        )

    def test_normalizers_bound_untrusted_fields(self) -> None:
        page = XQUIK_SEARCH._normalize_page(
            {
                "tweets": [
                    {
                        "id": "42",
                        "text": "x" * (XQUIK_SEARCH.MAX_RESULT_TEXT_LENGTH + 1),
                        "createdAt": "legacy",
                        "author": {"username": "not-valid!", "name": "Name"},
                        "likeCount": True,
                    }
                ],
                "has_next_page": True,
            }
        )
        tweet = page["tweets"][0]

        self.assertEqual(len(tweet["text"]), XQUIK_SEARCH.MAX_RESULT_TEXT_LENGTH)
        self.assertEqual(tweet["created_at"], "legacy")
        self.assertEqual(tweet["author"]["username"], "")
        self.assertEqual(tweet["url"], "")
        self.assertIsNone(tweet["metrics"]["likes"])
        self.assertIs(page["has_next_page"], True)
        self.assertEqual(XQUIK_SEARCH._author_data(None), ("", ""))
        self.assertEqual(XQUIK_SEARCH._tweet_url("not-an-id", "user"), "")

    def test_response_guards_handle_redirects_and_invalid_lengths(self) -> None:
        redirect = XQUIK_SEARCH.NoRedirectHandler().redirect_request(
            Request("https://xquik.com"),
            io.BytesIO(),
            302,
            "redirect",
            HTTPMessage(),
            "https://example.com",
        )
        invalid_length = FakeResponse({"tweets": []}, content_length="unknown")
        bounded_length = FakeResponse(
            {"tweets": []},
            content_length=str(len(FakeResponse({"tweets": []}).body)),
        )
        oversized_body = FakeResponse({"tweets": []})
        oversized_body.body = b"x" * (XQUIK_SEARCH.MAX_RESPONSE_BYTES + 1)

        self.assertIsNone(redirect)
        self.assertEqual(
            XQUIK_SEARCH._read_json(invalid_length),
            {"tweets": []},
        )
        self.assertEqual(
            XQUIK_SEARCH._read_json(bounded_length),
            {"tweets": []},
        )
        with self.assertRaisesRegex(ValueError, "size limit"):
            XQUIK_SEARCH._read_json(oversized_body)
        with self.assertRaisesRegex(TypeError, "malformed response"):
            XQUIK_SEARCH._normalize_page([])


class GuidanceTests(unittest.TestCase):
    def test_guidance_removes_unsupported_reach_guarantees(self) -> None:
        skill = (ROOT / ".claude" / "skills" / "x-boost" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        combined = f"{skill}\n{readme}".lower()

        self.assertNotIn("score = base_score", combined)
        self.assertNotIn("2-4 hours", combined)
        self.assertNotIn("maximum reach", combined)
        self.assertNotIn("algorithm secrets", combined)
        self.assertIn("context-dependent", combined)
        self.assertIn("https://github.com/xai-org/x-algorithm", readme)


if __name__ == "__main__":
    unittest.main()
