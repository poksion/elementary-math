from __future__ import annotations

import argparse
import html
import json
import mimetypes
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse


BASE_DIR = Path(__file__).resolve().parent
SCRIPT_NAME = Path(__file__).name


def list_data_files() -> list[Path]:
    return sorted(
        path
        for path in BASE_DIR.iterdir()
        if path.is_file() and path.name != SCRIPT_NAME and not path.name.startswith(".")
    )


class ElementaryMathHandler(BaseHTTPRequestHandler):
    server_version = "ElementaryMathServer/1.0"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        route = unquote(parsed.path)

        if route in {"/", "/index.html"}:
            self._serve_index()
            return

        if route == "/api/files":
            self._serve_file_list()
            return

        file_name = route.lstrip("/")
        if not file_name:
            self._send_error(HTTPStatus.NOT_FOUND, "Not found")
            return

        file_path = BASE_DIR / file_name
        if not self._is_allowed_file(file_path):
            self._send_error(HTTPStatus.NOT_FOUND, "File not found")
            return

        self._serve_file(file_path)

    def log_message(self, format: str, *args: object) -> None:
        print(f"[{self.log_date_time_string()}] {self.address_string()} - {format % args}")

    def _serve_index(self) -> None:
        items = []
        for file_path in list_data_files():
            size = file_path.stat().st_size
            escaped_name = html.escape(file_path.name)
            items.append(
                f'<li><a href="/{escaped_name}">{escaped_name}</a>'
                f' <span>{size} bytes</span></li>'
            )

        body = f"""<!doctype html>
<html lang="ko">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>elementary-math files</title>
    <style>
      :root {{
        color-scheme: light;
        font-family: "Segoe UI", sans-serif;
      }}
      body {{
        margin: 0;
        padding: 32px;
        background: #f6f7fb;
        color: #1f2937;
      }}
      main {{
        max-width: 720px;
        margin: 0 auto;
        background: white;
        border-radius: 16px;
        padding: 24px;
        box-shadow: 0 16px 40px rgba(15, 23, 42, 0.08);
      }}
      h1 {{
        margin-top: 0;
      }}
      ul {{
        padding-left: 20px;
      }}
      li {{
        margin: 10px 0;
      }}
      a {{
        color: #0f766e;
        text-decoration: none;
      }}
      a:hover {{
        text-decoration: underline;
      }}
      span {{
        color: #6b7280;
        margin-left: 8px;
      }}
      code {{
        background: #eef2ff;
        border-radius: 6px;
        padding: 2px 6px;
      }}
    </style>
  </head>
  <body>
    <main>
      <h1>elementary-math file server</h1>
      <p>이 서버는 현재 폴더의 데이터 파일만 제공합니다.</p>
      <p>JSON 목록: <a href="/api/files"><code>/api/files</code></a></p>
      <ul>
        {''.join(items) or '<li>No data files found.</li>'}
      </ul>
    </main>
  </body>
</html>
"""
        self._send_response(body.encode("utf-8"), "text/html; charset=utf-8")

    def _serve_file_list(self) -> None:
        payload = [
            {
                "name": file_path.name,
                "size": file_path.stat().st_size,
                "url": f"/{file_path.name}",
            }
            for file_path in list_data_files()
        ]
        self._send_response(
            json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8"),
            "application/json; charset=utf-8",
        )

    def _serve_file(self, file_path: Path) -> None:
        content = file_path.read_bytes()
        guessed_type, _ = mimetypes.guess_type(file_path.name)
        content_type = guessed_type or "text/plain; charset=utf-8"
        self._send_response(content, content_type)

    def _is_allowed_file(self, file_path: Path) -> bool:
        if not file_path.exists() or not file_path.is_file():
            return False
        if file_path.parent != BASE_DIR:
            return False
        if file_path.name == SCRIPT_NAME or file_path.name.startswith("."):
            return False
        return True

    def _send_response(self, content: bytes, content_type: str) -> None:
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(content)

    def _send_error(self, status: HTTPStatus, message: str) -> None:
        content = json.dumps({"error": message}, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(content)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Serve files from the elementary-math folder with Python standard library only."
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind. Default: 127.0.0.1")
    parser.add_argument("--port", default=8000, type=int, help="Port to bind. Default: 8000")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    server = ThreadingHTTPServer((args.host, args.port), ElementaryMathHandler)
    print(f"Serving {BASE_DIR} at http://{args.host}:{args.port}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()