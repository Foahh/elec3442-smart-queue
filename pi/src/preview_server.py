from __future__ import annotations

"""Minimal preview HTTP server."""

import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

if TYPE_CHECKING:
    from main import SharedState


class PreviewHTTPServer(ThreadingHTTPServer):
    """Threaded HTTP server exposing only the preview stream."""

    daemon_threads = True

    def __init__(
        self,
        server_address: tuple[str, int],
        shared_state: "SharedState",
    ) -> None:
        """Store runtime dependencies and initialize the server."""

        super().__init__(server_address, PreviewRequestHandler)
        self.shared_state = shared_state


class PreviewRequestHandler(BaseHTTPRequestHandler):
    """Serve only the MJPEG preview stream."""

    server: PreviewHTTPServer

    def do_GET(self) -> None:  # noqa: N802
        """Route GET requests to the preview stream."""

        path = urlparse(self.path).path.rstrip("/") or "/"
        try:
            if path == "/preview":
                self._handle_preview_stream()
                return
            self.send_error(HTTPStatus.NOT_FOUND)
        except BrokenPipeError:
            return
        except ConnectionResetError:
            return

    def log_message(self, format: str, *args: Any) -> None:
        """Silence default per-request stderr logging."""

    def _handle_preview_stream(self) -> None:
        self.server.shared_state.preview_client_connected()
        self.send_response(HTTPStatus.OK)
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
        self.end_headers()
        try:
            while True:
                jpg = self.server.shared_state.get_preview_jpeg()
                if jpg:
                    self.wfile.write(b"--frame\r\n")
                    self.wfile.write(b"Content-Type: image/jpeg\r\n")
                    self.wfile.write(
                        f"Content-Length: {len(jpg)}\r\n\r\n".encode("ascii")
                    )
                    self.wfile.write(jpg)
                    self.wfile.write(b"\r\n")
                    self.wfile.flush()
                time.sleep(0.03)
        finally:
            self.server.shared_state.preview_client_disconnected()


def create_preview_http_server(
    host: str,
    port: int,
    shared_state: "SharedState",
) -> PreviewHTTPServer:
    """Build the lightweight preview HTTP server."""

    return PreviewHTTPServer((host, port), shared_state=shared_state)
