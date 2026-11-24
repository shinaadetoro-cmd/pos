"""Local development server for Harvest POS and its optional AI assistant.

The server binds to loopback by default. Set OPENAI_API_KEY in the server
environment to enable model answers; the key is never sent to the browser.
"""
from __future__ import annotations

import json
import os
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
HOST = os.environ.get("POS_HOST", "127.0.0.1")
PORT = int(os.environ.get("POS_PORT", "8000"))
MODEL = os.environ.get("OPENAI_MODEL", "gpt-6.2-astra")
MAX_BODY = 48_000
MAX_QUESTION = 500

INSTRUCTIONS = """You are a careful financial operations assistant for a food business.
Use only the POS summary supplied with the question. Answer in plain language,
show the relevant numbers, and distinguish sales from gross profit. Gross profit
is sales less recorded product costs; it is not net profit and excludes wages,
rent, utilities, taxes, delivery costs, waste, and other expenses. Never invent
causes, costs, benchmarks, or business facts. Treat the 25% margin flag as a
prototype review threshold, not an industry standard. For a requested target
gross margin, calculate unit cost divided by one minus the target margin, and
label the result as a scenario rather than a pricing instruction. If the data is marked
sample, clearly say the result is illustrative. Give practical options and the
calculation behind them; don't make changes to prices or costs. If a question
asks for advice outside the supplied sales and product-cost data, say what data
is missing. Do not give personal investment, lending, tax, legal, or accounting
advice. Keep the answer concise."""


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def log_message(self, fmt, *args):
        # Keep questions, financial summaries, and provider responses out of logs.
        if self.path.startswith("/api/"):
            return
        super().log_message(fmt, *args)

    def _json(self, status: int, value: dict):
        body = json.dumps(value).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/api/status":
            self._json(200, {"aiEnabled": bool(os.environ.get("OPENAI_API_KEY")), "model": MODEL if os.environ.get("OPENAI_API_KEY") else None})
            return
        super().do_GET()

    def do_POST(self):
        if self.path != "/api/assistant":
            self._json(404, {"error": "Not found"})
            return
        key = os.environ.get("OPENAI_API_KEY")
        if not key:
            self._json(503, {"error": "AI is not configured. Local analysis is available."})
            return
        allowed_origins = {f"http://127.0.0.1:{PORT}", f"http://localhost:{PORT}"}
        if self.headers.get("Origin") not in allowed_origins:
            self._json(403, {"error": "Assistant requests must come from this local POS."})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length < 1 or length > MAX_BODY:
                self._json(413, {"error": "Request is empty or too large."})
                return
            body = json.loads(self.rfile.read(length))
            question = body.get("question") if isinstance(body, dict) else None
            context = body.get("context") if isinstance(body, dict) else None
            if not isinstance(question, str) or not question.strip() or len(question) > MAX_QUESTION:
                self._json(400, {"error": "Enter a question up to 500 characters."})
                return
            if not isinstance(context, dict):
                self._json(400, {"error": "POS summary is required."})
                return
            payload = json.dumps({"question": question.strip(), "pos_summary": context}, ensure_ascii=False)
            request = Request(
                "https://api.openai.com/v1/responses",
                data=json.dumps({"model": MODEL, "instructions": INSTRUCTIONS, "input": payload, "store": False}).encode("utf-8"),
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                method="POST",
            )
            with urlopen(request, timeout=35) as response:
                result = json.loads(response.read())
            answer = result.get("output_text")
            if not answer:
                chunks = []
                for item in result.get("output", []):
                    if item.get("type") == "message":
                        chunks.extend(part.get("text", "") for part in item.get("content", []) if part.get("type") == "output_text")
                answer = "\n".join(part for part in chunks if part)
            if not answer:
                self._json(502, {"error": "The AI service did not return an answer."})
                return
            self._json(200, {"answer": answer, "mode": "ai", "model": MODEL})
        except HTTPError as error:
            # Do not echo provider bodies, which can contain internal details.
            self._json(502, {"error": f"AI service returned HTTP {error.code}. Local analysis is still available."})
        except (URLError, TimeoutError, OSError):
            self._json(502, {"error": "Could not reach the AI service. Local analysis is still available."})
        except (json.JSONDecodeError, UnicodeDecodeError):
            self._json(400, {"error": "Request must contain valid JSON."})
        except Exception:
            self._json(500, {"error": "Assistant request failed. Local analysis is still available."})


if __name__ == "__main__":
    if HOST not in {"127.0.0.1", "localhost", "::1"}:
        raise SystemExit("For safety, this prototype server only binds to localhost. Add authentication and HTTPS before a hosted deployment.")
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Harvest POS running at http://{HOST}:{PORT}")
    if not os.environ.get("OPENAI_API_KEY"):
        print("AI is not configured; local financial analysis remains available.")
    server.serve_forever()
