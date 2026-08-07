"""
Remote resolution tests, run entirely against in-memory ports.

Nothing here opens a socket. That is the point of splitting retrieval into
`RevisionResolver`, `Fetcher`, and `Cache`: the whole remote path — pinning,
caching, admission, subdirectory selection, and every refusal — is exercisable
without a server, so these tests are as fast and as deterministic as the pure
ones.
"""

import io
import tarfile
import urllib.request
from pathlib import Path

import pytest

from spoc.scaffold.cache import DirectoryCache, default_cache_root
from spoc.scaffold.errors import (
    IncompleteTemplateSetError,
    InsecureRedirectError,
    RetrievalError,
    TemplateSetNotFoundError,
    UnrecognizedReferenceError,
)
from spoc.scaffold.plan import Reference
from spoc.scaffold.remote import HttpFetcher, _is_secure, _NoDowngradeRedirect
from spoc.scaffold.sources import InstalledTemplateSources, RemoteTemplateSource

MANIFEST = b"""
[template_set]
name = "remote"
description = "a set that arrived from elsewhere"
values = ["project_name"]

[[files]]
source = "main.py.tmpl"
target = "main.py"
"""


def _set_archive(prefix: str = "repo-abc123") -> bytes:
    """A tar shaped the way a forge serves one: a single wrapper directory."""
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        for name, payload in (
            (f"{prefix}/manifest.toml", MANIFEST),
            (f"{prefix}/main.py.tmpl", b"print('$project_name')\n"),
        ):
            info = tarfile.TarInfo(name)
            info.size = len(payload)
            archive.addfile(info, io.BytesIO(payload))
    return buffer.getvalue()


class FakeRevisions:
    def __init__(self, revision: str = "abc123") -> None:
        self.revision = revision
        self.calls = 0

    def resolve(self, reference: Reference) -> str:
        self.calls += 1
        return self.revision


class FakeFetcher:
    def __init__(self, payload: bytes | None = None) -> None:
        self.payload = payload if payload is not None else _set_archive()
        self.calls = 0

    def fetch(self, reference: Reference, revision: str) -> bytes:
        self.calls += 1
        return self.payload


class UnavailableFetcher:
    def fetch(self, reference: Reference, revision: str) -> bytes:
        raise RetrievalError(reference.raw, "the network is unavailable")


def _remote(tmp_path: Path, **overrides: object) -> tuple[RemoteTemplateSource, dict]:
    parts = {
        "revisions": FakeRevisions(),
        "fetcher": FakeFetcher(),
        "cache": DirectoryCache(tmp_path / "cache"),
    }
    parts.update(overrides)  # type: ignore[arg-type]
    return RemoteTemplateSource(**parts), parts  # type: ignore[arg-type]


class TestRemoteLoading:
    def test_remote_set_loads_like_a_local_one(self, tmp_path: Path) -> None:
        source, _ = _remote(tmp_path)
        loaded = source.load(_ref())
        assert loaded.name == "remote"
        assert [f.target for f in loaded.files] == ["main.py"]

    def test_forge_wrapper_directory_is_stepped_through(self, tmp_path: Path) -> None:
        """A forge wraps everything in one directory named for the revision.
        That is transport, not template set, so the author never sees it."""
        source, _ = _remote(tmp_path)
        loaded = source.load(_ref())
        assert loaded.name == "remote"


class TestCaching:
    def test_first_load_retrieves(self, tmp_path: Path) -> None:
        source, parts = _remote(tmp_path)
        source.load(_ref())
        assert parts["fetcher"].calls == 1

    def test_repeat_load_retrieves_nothing(self, tmp_path: Path) -> None:
        source, parts = _remote(tmp_path)
        source.load(_ref())
        source.load(_ref())
        assert parts["fetcher"].calls == 1, "a retained revision must not refetch"

    def test_retained_revision_survives_unavailable_retrieval(
        self, tmp_path: Path
    ) -> None:
        cache = DirectoryCache(tmp_path / "cache")
        working, _ = _remote(tmp_path, cache=cache)
        working.load(_ref())

        offline = RemoteTemplateSource(
            revisions=FakeRevisions(), fetcher=UnavailableFetcher(), cache=cache
        )
        assert offline.load(_ref()).name == "remote"

    def test_unretained_revision_without_retrieval_fails_actionably(
        self, tmp_path: Path
    ) -> None:
        offline = RemoteTemplateSource(
            revisions=FakeRevisions(),
            fetcher=UnavailableFetcher(),
            cache=DirectoryCache(tmp_path / "cache"),
        )
        with pytest.raises(RetrievalError) as caught:
            offline.load(_ref())
        assert "network is unavailable" in str(caught.value)
        assert "Nothing was written" in str(caught.value)

    def test_interrupted_retrieval_leaves_nothing_retained(
        self, tmp_path: Path
    ) -> None:
        cache = DirectoryCache(tmp_path / "cache")
        broken = RemoteTemplateSource(
            revisions=FakeRevisions(), fetcher=UnavailableFetcher(), cache=cache
        )
        with pytest.raises(RetrievalError):
            broken.load(_ref())
        assert cache.retained("abc123") is None


class TestSubdirectory:
    def test_named_subdirectory_is_used(self, tmp_path: Path) -> None:
        payload = _nested_archive()
        source, _ = _remote(tmp_path, fetcher=FakeFetcher(payload))
        loaded = source.load(_ref(subdirectory="sets/minimal"))
        assert loaded.name == "remote"

    def test_missing_subdirectory_names_what_was_missing(self, tmp_path: Path) -> None:
        payload = _nested_archive()
        source, _ = _remote(tmp_path, fetcher=FakeFetcher(payload))
        with pytest.raises(IncompleteTemplateSetError) as caught:
            source.load(_ref(subdirectory="sets/absent"))
        assert "sets/absent" in str(caught.value)


class TestDispatch:
    def test_remote_form_wins_over_a_same_spelled_local_directory(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Form is decided before existence is consulted. A directory literally
        named `gh:o` cannot be created on Windows, so this asserts the ordering
        the other way: a remote reference never reaches the directory loader."""
        remote, parts = _remote(tmp_path)
        sources = InstalledTemplateSources(remote)
        assert sources.load("gh:o/r").name == "remote"
        assert parts["fetcher"].calls == 1

    def test_remote_reference_without_wiring_is_not_found(self) -> None:
        with pytest.raises(TemplateSetNotFoundError):
            InstalledTemplateSources().load("gh:o/r")

    def test_unrecognized_scheme_is_not_reported_as_a_missing_directory(self) -> None:
        """The failure this whole restructure exists to prevent: before it,
        `ftp://x` was read as a path and complained about a missing manifest."""
        with pytest.raises(UnrecognizedReferenceError) as caught:
            InstalledTemplateSources().load("ftp://host/x.tar.gz")
        assert "manifest.toml" not in str(caught.value)

    def test_available_lists_only_enumerable_sources(self, tmp_path: Path) -> None:
        remote, _ = _remote(tmp_path)
        candidates = InstalledTemplateSources(remote).available()
        assert "default" in candidates
        assert not any(c.startswith("gh:") for c in candidates)


class TestRedirectPolicy:
    def test_https_to_http_is_refused(self) -> None:
        handler = _NoDowngradeRedirect()
        request = urllib.request.Request("https://host/set.tar.gz")
        with pytest.raises(InsecureRedirectError) as caught:
            handler.redirect_request(request, None, 302, "Found", {}, "http://host/x")
        assert "weaker guarantees" in str(caught.value)

    def test_https_to_https_is_allowed(self) -> None:
        handler = _NoDowngradeRedirect()
        request = urllib.request.Request("https://host/set.tar.gz")
        result = handler.redirect_request(
            request, None, 302, "Found", {}, "https://other/x"
        )
        assert result is not None

    def test_loopback_http_is_acceptable(self) -> None:
        assert _is_secure("http://localhost:8000/set.tar.gz")
        assert _is_secure("http://127.0.0.1/set.tar.gz")

    def test_remote_http_is_not_secure(self) -> None:
        assert not _is_secure("http://example.com/set.tar.gz")


class TestNoRemoteSuppliedPaths:
    def test_url_is_built_from_the_reference_alone(self) -> None:
        """Django's August 2026 advisory was a server-supplied filename reaching
        a path join. Nothing the remote party says may name anything locally, so
        the retrieval URL is a pure function of the reference and the revision."""
        fetcher = HttpFetcher()
        url = fetcher._url_for(_ref(), "abc123")
        assert url == "https://codeload.github.com/o/r/tar.gz/abc123"

    def test_hostile_content_disposition_places_no_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The exact shape of Django's advisory: a server answers with a filename
        that is an absolute path. It must reach nothing — the bytes are used, the
        name is not, and no file appears where the server asked for one."""
        import spoc.scaffold.remote as remote_module

        planted = tmp_path / "evil.tgz"
        payload = _set_archive()

        monkeypatch.setattr(
            remote_module,
            "_opener",
            lambda: _FakeOpener(
                payload, disposition=f'attachment; filename="{planted}"'
            ),
        )

        got = HttpFetcher().fetch(_ref(), "abc123")

        assert got == payload
        assert not planted.exists(), "a server-supplied filename must name nothing"


class TestCacheRoot:
    def test_xdg_override_is_honoured(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("XDG_CACHE_HOME", "/tmp/somewhere")
        assert "somewhere" in str(default_cache_root())

    def test_root_is_under_a_spoc_directory(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("XDG_CACHE_HOME", raising=False)
        assert "spoc" in str(default_cache_root()).lower()


class _FakeResponse:
    """A response carrying headers a hostile server would like us to read."""

    def __init__(self, payload: bytes, disposition: str) -> None:
        self._buffer = io.BytesIO(payload)
        self.headers = {"Content-Disposition": disposition, "Content-Length": "999999"}

    def read(self, size: int = -1) -> bytes:
        return self._buffer.read(size)

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *exc: object) -> None:
        return None


class _FakeOpener:
    def __init__(self, payload: bytes, disposition: str) -> None:
        self._payload = payload
        self._disposition = disposition

    def open(self, request: object, timeout: float | None = None) -> _FakeResponse:
        return _FakeResponse(self._payload, self._disposition)


def _ref(subdirectory: str | None = None) -> Reference:
    from spoc.scaffold.plan import ReferenceKind

    return Reference(
        kind=ReferenceKind.REMOTE,
        raw="gh:o/r",
        scheme="gh",
        location="o/r",
        subdirectory=subdirectory,
    )


def _nested_archive() -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        for name, payload in (
            ("repo-abc/sets/minimal/manifest.toml", MANIFEST),
            ("repo-abc/sets/minimal/main.py.tmpl", b"print('$project_name')\n"),
        ):
            info = tarfile.TarInfo(name)
            info.size = len(payload)
            archive.addfile(info, io.BytesIO(payload))
    return buffer.getvalue()
