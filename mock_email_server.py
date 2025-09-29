"""Simple HTTP mock for external email API."""

from __future__ import annotations

import json
import logging
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any


logging.basicConfig(level=logging.INFO, format="[MOCK-EMAIL] %(message)s")
LOGGER = logging.getLogger("mock_email")


class EmailRequestHandler(BaseHTTPRequestHandler):
    server_version = "MockEmail/1.0"

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003 - required signature
        LOGGER.info(format, *args)

    def do_POST(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
        content_length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(content_length)
        try:
            payload = json.loads(body.decode("utf-8"))
        except json.JSONDecodeError:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"{\"detail\": \"Invalid JSON\"}")
            return

        LOGGER.info(
            "Email dispatched to=%s subject=%s body=%s",
            payload.get("to"),
            payload.get("subject"),
            payload.get("body"),
        )

        response = json.dumps({"status": "ok"}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)


def run(host: str = "0.0.0.0", port: int = 8080) -> None:
    LOGGER.info("Starting mock email API on %s:%s", host, port)
    server = HTTPServer((host, port), EmailRequestHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:  # pragma: no cover - manual stop
        pass
    finally:
        server.server_close()
        LOGGER.info("Mock email API stopped")


if __name__ == "__main__":
    run()
