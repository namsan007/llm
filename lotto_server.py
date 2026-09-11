from __future__ import annotations

import json
import sqlite3
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).parent
CACHE_DIR = ROOT / ".cache"
DATABASE = CACHE_DIR / "lotto_data.db"
DATABASE_URL = "https://raw.githubusercontent.com/happylie/lotto_data/main/lotto_data.db"


def ensure_database() -> None:
    if DATABASE.exists():
        return
    CACHE_DIR.mkdir(exist_ok=True)
    urllib.request.urlretrieve(DATABASE_URL, DATABASE)


class LottoHandler(SimpleHTTPRequestHandler):
    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/history":
            self.send_history(parse_qs(parsed.query))
            return
        if parsed.path == "/":
            self.path = "/game04/index.html"
        super().do_GET()

    def send_history(self, query: dict[str, list[str]]) -> None:
        start = max(1, int(query.get("start", [1])[0]))
        end = max(start, int(query.get("end", [9999])[0]))
        ensure_database()
        with sqlite3.connect(DATABASE) as connection:
            rows = connection.execute(
                'SELECT round, "1st", "2nd", "3rd", "4th", "5th", "6th", bonus '
                "FROM tb_lotto_list WHERE round BETWEEN ? AND ? ORDER BY round",
                (start, end),
            ).fetchall()
        payload = [
            {"draw": row[0], "numbers": list(row[1:7]), "bonus": row[7]}
            for row in rows
        ]
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", 8000), LottoHandler)
    print("로또 분석기: http://127.0.0.1:8000/game04/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()