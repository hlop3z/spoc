"""
Remote resolution tests, run entirely against in-memory ports.

Nothing here opens a socket. That is the point of splitting retrieval into
`RevisionResolver`, `Fetcher`, and `Cache`: the whole remote path — pinning,
caching, admission, subdirectory selection, and every refusal — is exercisable
without a server, so these tests are as fast and as deterministic as the pure
ones.
"""

import email.message
import io
import json
import tarfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import Self

import pytest

from spoc.scaffold import remote
from spoc.scaffold.cache import DirectoryCache
from spoc.scaffold.core import parse_reference
from spoc.scaffold.errors import (
    IncompleteTemplateSetError,
    InsecureRedirectError,
    RetrievalError,
    TemplateSetNotFoundError,
    UnrecognizedReferenceError,
)
from spoc.scaffold.plan import Reference, ReferenceKind
from spoc.scaffold.remote import HttpFetcher, _is_secure, _NoDowngradeRedirect
from spoc.scaffold.sources import InstalledTemplateSources, RemoteTemplateSource

# The socket ban is what makes this module's opening claim checkable rather than
# aspirational — see the `no_sockets` fixture in conftest.py.
pytestmark = pytest.mark.usefixtures("no_sockets")

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

    def test_the_refusing_handler_is_actually_installed(self) -> None:
        """The tests above prove the handler refuses a downgrade. This proves the
        opener every retrieval uses is the one carrying it — without this, the
        policy could be correct and unreachable at the same time, and every other
        test in this class would still pass."""
        # `handlers` is not in the type stubs, so it is read defensively: if it
        # ever disappears this reads as no handler installed and fails, which is
        # the honest outcome for a test that can no longer see what it checks.
        installed = getattr(remote._opener(), "handlers", [])
        assert any(isinstance(h, _NoDowngradeRedirect) for h in installed), (
            "retrievals would follow a redirect onto plaintext without being asked"
        )


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


class _FakeResponse:
    """A response carrying headers a hostile server would like us to read."""

    def __init__(self, payload: bytes, disposition: str) -> None:
        self._buffer = io.BytesIO(payload)
        self.headers = {"Content-Disposition": disposition, "Content-Length": "999999"}

    def read(self, size: int = -1) -> bytes:
        return self._buffer.read(size)

    def __enter__(self) -> Self:
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


class TestFailuresNameWhatTheCallerSupplied:
    """A caller can only correct what they typed.

    The adapter derives `https://api.github.com/repos/o/r/commits/HEAD` from
    `gh:o/r`; naming the derived URL alone points at something the author never
    chose and cannot act on.
    """

    @staticmethod
    def _breaking_opener(error: Exception) -> object:
        class Opener:
            def open(self, request: object, timeout: float | None = None) -> object:
                raise error

        return lambda: Opener()

    def test_http_error_names_the_reference(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            remote,
            "_opener",
            self._breaking_opener(
                urllib.error.HTTPError(
                    "https://api.github.com/repos/o/r/commits/HEAD",
                    404,
                    "Not Found",
                    email.message.Message(),
                    None,
                )
            ),
        )
        reference = Reference(
            kind=ReferenceKind.REMOTE, raw="gh:o/r", scheme="gh", location="o/r"
        )
        with pytest.raises(RetrievalError) as caught:
            remote.HttpRevisionResolver().resolve(reference)

        message = str(caught.value)
        assert "'gh:o/r'" in message
        assert "404" in message
        assert not message.startswith("Could not retrieve template set 'https://")

    def test_transport_error_names_the_reference(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            remote, "_opener", self._breaking_opener(OSError("name resolution failed"))
        )
        reference = Reference(
            kind=ReferenceKind.REMOTE, raw="gh:o/r", scheme="gh", location="o/r"
        )
        with pytest.raises(RetrievalError) as caught:
            remote.HttpFetcher().fetch(reference, "abc123")

        message = str(caught.value)
        assert "'gh:o/r'" in message
        assert "name resolution failed" in message


class _PayloadOpener:
    """An opener answering with exactly these bytes, and no useful headers."""

    def __init__(self, payload: bytes) -> None:
        self.payload = payload
        self.calls = 0

    def open(self, request: object, timeout: float | None = None) -> _FakeResponse:
        self.calls += 1
        return _FakeResponse(self.payload, disposition="")


def _answering(payload: bytes) -> _PayloadOpener:
    return _PayloadOpener(payload)


class TestTransferBound:
    """`MAX_TRANSFER_BYTES` refuses an absurd transfer before it is buffered.

    The bound that decides correctness is the expanded-size one in
    `spoc.scaffold.archive`; this one exists so a hostile server cannot make the
    process hold 96MB in memory on the way there. The real constant is far too
    large to allocate in a test, so the bound itself is moved rather than the
    payload — what is under test is the comparison, not the number.
    """

    def test_a_transfer_over_the_bound_is_refused(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(remote, "MAX_TRANSFER_BYTES", 16)
        monkeypatch.setattr(remote, "_opener", lambda: _answering(b"x" * 17))

        with pytest.raises(RetrievalError) as caught:
            remote.HttpFetcher().fetch(_ref(), "abc123")

        message = str(caught.value)
        assert "16" in message, "the failure must name the bound that was exceeded"
        assert "'gh:o/r'" in message

    def test_a_transfer_exactly_at_the_bound_is_accepted(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The bound is a maximum, not a strict one — an exact fit is not an
        excess, and an off-by-one here would refuse legitimate content."""
        monkeypatch.setattr(remote, "MAX_TRANSFER_BYTES", 16)
        monkeypatch.setattr(remote, "_opener", lambda: _answering(b"x" * 16))

        assert remote.HttpFetcher().fetch(_ref(), "abc123") == b"x" * 16


class TestInsecureRedirectSurvivesRetrieval:
    def test_a_refused_redirect_is_not_flattened_into_a_generic_failure(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The redirect policy is only as good as what the caller is told. If the
        refusal were reported as an ordinary retrieval failure, a downgrade attack
        would be indistinguishable from a flaky network."""

        class Opener:
            def open(self, request: object, timeout: float | None = None) -> object:
                raise InsecureRedirectError(
                    "https://host/set.tar.gz", "http://host/set.tar.gz"
                )

        monkeypatch.setattr(remote, "_opener", lambda: Opener())

        with pytest.raises(InsecureRedirectError) as caught:
            remote.HttpFetcher().fetch(_ref(), "abc123")
        assert "weaker guarantees" in str(caught.value)


class TestMalformedGithubReference:
    @pytest.mark.parametrize("location", ["o", "o/r/extra", "", "/"])
    def test_a_reference_that_is_not_owner_repo_is_refused(self, location: str) -> None:
        reference = Reference(
            kind=ReferenceKind.REMOTE,
            raw=f"gh:{location}",
            scheme="gh",
            location=location,
        )
        with pytest.raises(RetrievalError) as caught:
            remote.HttpRevisionResolver().resolve(reference)

        message = str(caught.value)
        assert "owner/repo" in message, "the failure must say what the form should be"
        assert f"'gh:{location}'" in message

    def test_the_same_refusal_applies_when_building_a_url(self) -> None:
        reference = Reference(
            kind=ReferenceKind.REMOTE, raw="gh:o", scheme="gh", location="o"
        )
        with pytest.raises(RetrievalError):
            remote.HttpFetcher().fetch(reference, "abc123")


class TestRevisionResolution:
    """Every form a reference can take, resolved to the revision it designates."""

    def test_a_github_reference_resolves_to_the_reported_commit(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        opener = _answering(json.dumps({"sha": "d3adb33f"}).encode("utf-8"))
        monkeypatch.setattr(remote, "_opener", lambda: opener)

        assert remote.HttpRevisionResolver().resolve(_ref()) == "d3adb33f"
        assert opener.calls == 1, "a moving reference has to be asked about"

    @pytest.mark.parametrize(
        "payload",
        [
            b"not json at all",
            b"{}",
            b"[]",
            b'{"commit": {"sha": "abc"}}',
            b"null",
        ],
    )
    def test_a_response_without_a_revision_is_refused(
        self, monkeypatch: pytest.MonkeyPatch, payload: bytes
    ) -> None:
        """Nothing the remote party says is trusted to be well-formed."""
        monkeypatch.setattr(remote, "_opener", lambda: _answering(payload))

        with pytest.raises(RetrievalError) as caught:
            remote.HttpRevisionResolver().resolve(_ref())
        assert "did not report a revision" in str(caught.value)
        assert "'gh:o/r'" in str(caught.value)

    def test_a_pinned_reference_resolves_without_asking_anyone(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A pinned VCS reference already names its revision, so resolving it is
        a pure function and must open nothing."""
        opener = _answering(b'{"sha": "should-not-be-read"}')
        monkeypatch.setattr(remote, "_opener", lambda: opener)

        reference = parse_reference("git+https://host/o/repo@v1.2.3")
        assert remote.HttpRevisionResolver().resolve(reference) == "v1.2.3"
        assert opener.calls == 0

    def test_a_direct_archive_url_is_keyed_by_its_own_digest(self) -> None:
        """A direct URL carries no revision to ask about, so the URL is the whole
        identity and its digest is the key."""
        reference = parse_reference("https://host/sets/minimal.tar.gz")
        revision = remote.HttpRevisionResolver().resolve(reference)
        assert revision.startswith("url-")

    def test_the_same_url_always_yields_the_same_key(self) -> None:
        """Otherwise a repeat generation would retrieve again every time."""
        first = remote.HttpRevisionResolver().resolve(
            parse_reference("https://host/set.tar.gz")
        )
        second = remote.HttpRevisionResolver().resolve(
            parse_reference("https://host/set.tar.gz")
        )
        assert first == second

    def test_different_urls_yield_different_keys(self) -> None:
        resolver = remote.HttpRevisionResolver()
        first = resolver.resolve(parse_reference("https://host/one.tar.gz"))
        second = resolver.resolve(parse_reference("https://host/two.tar.gz"))
        assert first != second


class TestRetrievalUrlConstruction:
    """The URL is a pure function of the reference and the revision.

    Every case here is the same assertion in a different dress: what is fetched
    is derived locally, never taken from anything a remote party said.
    """

    @pytest.mark.parametrize(
        ("reference", "expected"),
        [
            (
                "gh:o/r",
                "https://codeload.github.com/o/r/tar.gz/abc123",
            ),
            (
                "git+https://host/o/repo",
                "https://host/o/repo/archive/abc123.tar.gz",
            ),
            # The `.git` suffix is transport spelling, not part of the path.
            (
                "git+https://host/o/repo.git",
                "https://host/o/repo/archive/abc123.tar.gz",
            ),
            (
                "git+ssh://host/o/repo",
                "ssh://host/o/repo/archive/abc123.tar.gz",
            ),
            # A direct archive URL is used exactly as supplied. Plaintext here is
            # the caller's explicit choice; what is refused is being *moved* onto
            # plaintext by a redirect nobody asked for.
            (
                "https://host/sets/minimal.tar.gz",
                "https://host/sets/minimal.tar.gz",
            ),
            (
                "http://localhost:8000/set.tar.gz",
                "http://localhost:8000/set.tar.gz",
            ),
        ],
    )
    def test_url_is_derived_from_the_reference_alone(
        self, reference: str, expected: str
    ) -> None:
        built = HttpFetcher()._url_for(parse_reference(reference), "abc123")
        assert built == expected
