# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Measure what an editor's completion list actually costs, per stub shape.

The conformance gate proves a checker *accepts* a generated stub. It says
nothing about the experience the developer has typing against one, which is a
different question with a different failure mode: a stub can be perfectly
correct and still take twenty seconds to offer a completion.

This drives the real language servers over stdio — the same processes an editor
runs — and reports latency, item count, and whether the expected entry was
offered. Two requests per case: the first includes the server's first analysis
(opening a file and typing), the second is steady state.

mypy has no language server and is absent by nature, not by omission. pyright is
the engine behind Pylance, which makes it the authority on the claim.

    uv run scripts/py/lab/completion_bench.py <workspace> <line> <character>
    uv run scripts/py/lab/completion_bench.py demo/ 1 21 --expect model_0

The workspace is a directory holding a `probe.py` and whatever stub it imports;
line/character place the cursor mid-typing (0-indexed, as LSP counts). Build the
workspace however you like — that part is deliberately not this script's job, so
it can measure any shape rather than the ones it knows how to generate.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import subprocess
import sys
import time
from pathlib import Path

SESSION_TIMEOUT = 180


class Lsp:
    """A language server over stdio, spoken to in the smallest useful subset."""

    def __init__(self, argv: list[str], deadline: float) -> None:
        self.proc = subprocess.Popen(
            argv,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        self.deadline = deadline
        self.next_id = 0

    def send(self, method: str, params: dict, *, notify: bool = False) -> int | None:
        message: dict = {"jsonrpc": "2.0", "method": method, "params": params}
        if not notify:
            self.next_id += 1
            message["id"] = self.next_id
        self._write(message)
        return None if notify else self.next_id

    def _write(self, message: dict) -> None:
        raw = json.dumps(message).encode()
        assert self.proc.stdin is not None
        self.proc.stdin.write(f"Content-Length: {len(raw)}\r\n\r\n".encode() + raw)
        self.proc.stdin.flush()

    def _read(self) -> dict:
        assert self.proc.stdout is not None
        headers: dict[str, str] = {}
        while True:
            if time.monotonic() > self.deadline:
                raise TimeoutError("server did not answer within the session budget")
            line = self.proc.stdout.readline()
            if not line:
                raise ConnectionError("server closed stdout")
            if line in (b"\r\n", b"\n"):
                break
            key, _, value = line.decode().partition(":")
            headers[key.strip().lower()] = value.strip()
        return json.loads(self.proc.stdout.read(int(headers["content-length"])))

    def wait_for(self, request_id: int) -> dict:
        while True:
            message = self._read()
            if message.get("id") == request_id and (
                "result" in message or "error" in message
            ):
                return message
            # Server-initiated requests must be answered or some servers stall
            # waiting for a reply that never comes.
            if "id" in message and "method" in message:
                self._write({"jsonrpc": "2.0", "id": message["id"], "result": None})

    def close(self) -> None:
        with contextlib.suppress(OSError):  # already gone is the same outcome
            self.proc.kill()


def _items(reply: dict) -> list[dict]:
    payload = reply.get("result")
    if payload is None:
        return []
    return payload if isinstance(payload, list) else payload.get("items", [])


def measure(
    server: str, argv: list[str], workspace: Path, line: int, char: int, expect: str
) -> None:
    uri = (workspace / "probe.py").as_uri()
    text = (workspace / "probe.py").read_text(encoding="utf-8")
    lsp = Lsp(argv, time.monotonic() + SESSION_TIMEOUT)
    try:
        opened = lsp.send(
            "initialize",
            {
                "processId": None,
                "rootUri": workspace.as_uri(),
                "capabilities": {"textDocument": {"completion": {}}},
                "workspaceFolders": [
                    {"uri": workspace.as_uri(), "name": workspace.name}
                ],
            },
        )
        assert opened is not None
        lsp.wait_for(opened)
        lsp.send("initialized", {}, notify=True)
        lsp.send(
            "textDocument/didOpen",
            {
                "textDocument": {
                    "uri": uri,
                    "languageId": "python",
                    "version": 1,
                    "text": text,
                }
            },
            notify=True,
        )

        timings: list[float] = []
        offered: list[dict] = []
        for _ in range(2):
            start = time.perf_counter()
            request = lsp.send(
                "textDocument/completion",
                {
                    "textDocument": {"uri": uri},
                    "position": {"line": line, "character": char},
                },
            )
            assert request is not None
            offered = _items(lsp.wait_for(request))
            timings.append(time.perf_counter() - start)

        found = any(expect in (item.get("label") or "") for item in offered)
        print(
            f"{server:<10} cold {timings[0]:>7.2f}s  warm {timings[1]:>7.2f}s  "
            f"items {len(offered):>6}  {expect!r} {'offered' if found else 'MISSING'}"
        )
    except (TimeoutError, ConnectionError) as exc:
        print(f"{server:<10} unusable: {exc}")
    finally:
        lsp.close()


def _nearest_venv() -> Path | None:
    """The closest `.venv` at or above the working directory."""
    for directory in (Path.cwd(), *Path.cwd().parents):
        candidate = directory / ".venv"
        if candidate.is_dir():
            return candidate
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("workspace", type=Path, help="directory holding probe.py")
    parser.add_argument("line", type=int, help="cursor line, 0-indexed")
    parser.add_argument("character", type=int, help="cursor column, 0-indexed")
    parser.add_argument(
        "--expect", default="", help="substring a correct completion list must offer"
    )
    parser.add_argument(
        "--venv",
        type=Path,
        default=None,
        help="environment holding the language servers (default: the nearest .venv)",
    )
    args = parser.parse_args()

    # Not `sys.prefix`: run as a PEP 723 script this file gets its own ephemeral
    # environment, which has no language servers in it. The servers live in the
    # project's venv, so that is what to drive unless told otherwise.
    if args.venv is None:
        args.venv = _nearest_venv() or Path(sys.prefix)

    if not (args.workspace / "probe.py").is_file():
        parser.error(f"{args.workspace}/probe.py does not exist")

    scripts = args.venv / ("Scripts" if sys.platform == "win32" else "bin")
    suffix = ".exe" if sys.platform == "win32" else ""
    servers = {
        "pyright": [str(scripts / f"pyright-langserver{suffix}"), "--stdio"],
        "ty": [str(scripts / f"ty{suffix}"), "server"],
    }

    for server, argv in servers.items():
        if not Path(argv[0]).exists():
            print(f"{server:<10} not installed at {argv[0]}")
            continue
        measure(server, argv, args.workspace, args.line, args.character, args.expect)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
