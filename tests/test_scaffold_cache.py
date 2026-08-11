"""
Retention tests: where retained content goes, what it is keyed by, and what two
operations racing for the same revision do to each other.

Nothing here opens a socket, and nothing here depends on the platform it runs on.
Both properties are deliberate. The first is the same one `test_scaffold_remote.py`
holds. The second is what `platform-support` requires: `cache_root_for` takes the
platform as an argument, so every arm is exercised from every host and this file
reports the same coverage on Windows, macOS, and Linux.
"""

from pathlib import Path

import pytest

from spoc.scaffold.cache import (
    APPLICATION_NAME,
    DirectoryCache,
    cache_root_for,
    default_cache_root,
)
from spoc.scaffold.errors import RetrievalError
from spoc.scaffold.plan import Reference, ReferenceKind
from spoc.scaffold.remote import HttpRevisionResolver
from spoc.scaffold.sources import RemoteTemplateSource

# Enforced, not just asserted in the docstring above — see conftest.py.
pytestmark = pytest.mark.usefixtures("no_sockets")

HOME = Path("/home/dev")

# Every platform the project declares, named as a value. The point of the list is
# that a contributor on any one of them exercises all three.
PLATFORMS = ["win32", "darwin", "linux"]


class TestCacheRootPerPlatform:
    """Each platform's convention, reachable from every platform."""

    @pytest.mark.parametrize(
        ("platform", "environ", "expected"),
        [
            ("win32", {"LOCALAPPDATA": "/local"}, Path("/local")),
            # APPDATA is the documented fallback when LOCALAPPDATA is absent.
            ("win32", {"APPDATA": "/roaming"}, Path("/roaming")),
            ("win32", {}, HOME / "AppData" / "Local"),
            ("darwin", {}, HOME / "Library" / "Caches"),
            ("linux", {}, HOME / ".cache"),
            # An unfamiliar POSIX platform falls to the same convention as Linux
            # rather than to no answer at all.
            ("freebsd14", {}, HOME / ".cache"),
        ],
    )
    def test_platform_convention_is_followed(
        self, platform: str, environ: dict, expected: Path
    ) -> None:
        root = cache_root_for(platform, environ, HOME)
        assert expected in root.parents

    @pytest.mark.parametrize("platform", PLATFORMS)
    def test_override_wins_on_every_platform(self, platform: str) -> None:
        """A user who set XDG_CACHE_HOME has said where cached data goes. That
        answer outranks the platform default everywhere, not only where it is
        native to the platform."""
        root = cache_root_for(platform, {"XDG_CACHE_HOME": "/stated"}, HOME)
        assert Path("/stated") in root.parents

    @pytest.mark.parametrize("platform", PLATFORMS)
    def test_override_outranks_a_native_default(self, platform: str) -> None:
        """Set together, the stated location wins over the platform's own."""
        environ = {"XDG_CACHE_HOME": "/stated", "LOCALAPPDATA": "/local"}
        root = cache_root_for(platform, environ, HOME)
        assert Path("/stated") in root.parents
        assert Path("/local") not in root.parents

    @pytest.mark.parametrize("platform", PLATFORMS)
    def test_retention_is_namespaced_to_the_project(self, platform: str) -> None:
        """Removing the directory must remove this project's retained content and
        nobody else's."""
        root = cache_root_for(platform, {}, HOME)
        assert APPLICATION_NAME in root.parts

    def test_adapter_reads_the_running_platform(self) -> None:
        """`default_cache_root` holds no logic of its own — it supplies the
        ambient platform, environment, and home to the function above."""
        assert APPLICATION_NAME in str(default_cache_root()).lower()


class TestRevisionNamesItsOwnContent:
    """A revision must designate its own retained content and no other's."""

    def test_a_safe_revision_is_used_verbatim(self, tmp_path: Path) -> None:
        """Every revision reachable through the reference grammar today is already
        a safe segment, so nothing retained before this mapping is invalidated."""
        cache = DirectoryCache(tmp_path)
        assert cache._entry("a1b2c3d4").name == "a1b2c3d4"
        assert cache._entry("v1.0.0").name == "v1.0.0"
        assert cache._entry("release-1_0").name == "release-1_0"

    @pytest.mark.parametrize(
        ("left", "right"),
        [
            # The collision that motivated this: filtering the separator out made
            # a branch-shaped revision indistinguishable from a bare one.
            ("feature/x", "featurex"),
            ("a/b/c", "abc"),
            # Both filter to nothing, and both used to land on the literal
            # `invalid`, so every unusable revision shared one entry.
            ("..", "/"),
            ("/", "?"),
            # Differs only where the old filter dropped characters.
            ("v1/0", "v10"),
        ],
    )
    def test_distinct_revisions_never_share_content(
        self, tmp_path: Path, left: str, right: str
    ) -> None:
        cache = DirectoryCache(tmp_path)
        assert cache._entry(left) != cache._entry(right)

    @pytest.mark.parametrize(
        "revision", ["..", "../..", "../../etc/passwd", "/etc/passwd", "..\\..\\win"]
    )
    def test_a_revision_cannot_escape_the_retention_root(
        self, tmp_path: Path, revision: str
    ) -> None:
        root = tmp_path / "cache"
        entry = DirectoryCache(root)._entry(revision)
        assert root in entry.parents, "a revision must not designate a location outside"
        assert entry.parent == root

    def test_the_same_revision_is_stable_across_calls(self, tmp_path: Path) -> None:
        """Keying is a pure function of the revision: a repeat generation has to
        find what the first one retained."""
        cache = DirectoryCache(tmp_path)
        assert cache._entry("feature/x") == cache._entry("feature/x")

    def test_a_url_digest_key_survives_verbatim(self, tmp_path: Path) -> None:
        """`HttpRevisionResolver` keys a direct archive URL as `url-<digest>`. That
        is already a safe segment, so this mapping leaves it exactly as it was."""
        reference = Reference(
            kind=ReferenceKind.REMOTE,
            raw="https://host/set.tar.gz",
            scheme="https",
            location="//host/set.tar.gz",
        )
        revision = HttpRevisionResolver().resolve(reference)
        assert revision.startswith("url-")
        assert DirectoryCache(tmp_path)._entry(revision).name == revision


class TestEmptyRevision:
    """An empty revision designates nothing, so there is nothing to retain."""

    def test_empty_revision_is_refused_naming_the_reference(
        self, tmp_path: Path
    ) -> None:
        source = RemoteTemplateSource(
            revisions=_EmptyRevisions(),
            fetcher=_UnusedFetcher(),
            cache=DirectoryCache(tmp_path),
        )
        reference = Reference(
            kind=ReferenceKind.REMOTE, raw="gh:o/r", scheme="gh", location="o/r"
        )
        with pytest.raises(RetrievalError) as caught:
            source.load(reference)

        message = str(caught.value)
        assert "'gh:o/r'" in message, "the caller can only correct what they typed"
        assert "Nothing was written" in message

    def test_nothing_is_retrieved_for_an_empty_revision(self, tmp_path: Path) -> None:
        fetcher = _UnusedFetcher()
        source = RemoteTemplateSource(
            revisions=_EmptyRevisions(), fetcher=fetcher, cache=DirectoryCache(tmp_path)
        )
        with pytest.raises(RetrievalError):
            source.load(
                Reference(
                    kind=ReferenceKind.REMOTE, raw="gh:o/r", scheme="gh", location="o/r"
                )
            )
        assert fetcher.calls == 0


class TestConcurrentRetention:
    """Two operations retaining one revision at the same time.

    The race is provoked at the publish seam rather than with real threads: the
    postconditions are identical, and this cannot become the suite's one flaky
    test. What it does not prove is that the platform's own rename is atomic —
    that is what running the gate on each declared platform is for.
    """

    @staticmethod
    def _publish_losing_to(other: Path):
        """A publish that fails because another process got there first."""

        def replace(self: Path, target) -> Path:
            Path(target).mkdir(parents=True, exist_ok=True)
            (Path(target) / "from-the-winner.txt").write_text(
                "winner", encoding="utf-8"
            )
            raise OSError("another process published this revision first")

        return replace

    @staticmethod
    def _publish_failing(self: Path, target) -> Path:
        raise OSError("the filesystem refused the rename")

    def test_losing_the_race_yields_the_published_revision(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        cache = DirectoryCache(tmp_path / "cache")
        entry = cache._entry("abc123")
        monkeypatch.setattr(Path, "replace", self._publish_losing_to(entry))

        result = cache.retain("abc123", lambda staging: _populate(staging))

        assert result == entry
        assert (result / "from-the-winner.txt").exists(), (
            "the revision is immutable, so the copy that landed first is correct"
        )

    def test_the_loser_leaves_no_staged_content_behind(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        root = tmp_path / "cache"
        cache = DirectoryCache(root)
        monkeypatch.setattr(Path, "replace", self._publish_losing_to(cache._entry("x")))

        cache.retain("x", lambda staging: _populate(staging))

        leftovers = [p.name for p in root.iterdir() if p.name.startswith(".staging-")]
        assert leftovers == [], f"staged content was left in the cache: {leftovers}"

    def test_a_publish_failure_is_not_disguised_as_a_race(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When the publish fails and the revision is not there afterwards, the
        failure is real and must surface rather than be reported as retained."""
        cache = DirectoryCache(tmp_path / "cache")
        monkeypatch.setattr(Path, "replace", self._publish_failing)

        with pytest.raises(OSError, match="refused the rename"):
            cache.retain("abc123", lambda staging: _populate(staging))

        assert cache.retained("abc123") is None

    def test_a_failed_publish_leaves_nothing_staged(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        root = tmp_path / "cache"
        cache = DirectoryCache(root)
        monkeypatch.setattr(Path, "replace", self._publish_failing)

        with pytest.raises(OSError):
            cache.retain("abc123", lambda staging: _populate(staging))

        assert [p.name for p in root.iterdir() if p.name.startswith(".staging-")] == []

    def test_an_already_retained_revision_is_not_repopulated(
        self, tmp_path: Path
    ) -> None:
        cache = DirectoryCache(tmp_path / "cache")
        cache.retain("abc123", lambda staging: _populate(staging))

        calls = 0

        def populate(staging: Path) -> None:
            nonlocal calls
            calls += 1
            _populate(staging)

        cache.retain("abc123", populate)
        assert calls == 0, "a retained revision must not be populated again"

    def test_an_interrupted_population_retains_nothing(self, tmp_path: Path) -> None:
        cache = DirectoryCache(tmp_path / "cache")

        def failing(staging: Path) -> None:
            _populate(staging)
            raise RuntimeError("retrieval died partway through")

        with pytest.raises(RuntimeError):
            cache.retain("abc123", failing)

        assert cache.retained("abc123") is None
        root = tmp_path / "cache"
        assert [p.name for p in root.iterdir() if p.name.startswith(".staging-")] == []


class TestRetained:
    def test_an_unretained_revision_reports_nothing(self, tmp_path: Path) -> None:
        assert DirectoryCache(tmp_path)._entry("abc") is not None
        assert DirectoryCache(tmp_path).retained("abc") is None

    def test_a_retained_revision_reports_its_location(self, tmp_path: Path) -> None:
        cache = DirectoryCache(tmp_path / "cache")
        entry = cache.retain("abc123", lambda staging: _populate(staging))
        assert cache.retained("abc123") == entry

    def test_a_file_is_not_a_retained_revision(self, tmp_path: Path) -> None:
        """Retention is a directory. Anything else at that location is not it."""
        cache = DirectoryCache(tmp_path / "cache")
        entry = cache._entry("abc123")
        entry.parent.mkdir(parents=True, exist_ok=True)
        entry.write_text("not a directory", encoding="utf-8")
        assert cache.retained("abc123") is None


def _populate(staging: Path) -> None:
    """Write something recognizable into a staging directory."""
    (staging / "manifest.toml").write_text("[template_set]\n", encoding="utf-8")


class _EmptyRevisions:
    """A resolver whose answer designates nothing — what a host reporting an empty
    `sha` would produce."""

    def resolve(self, reference: Reference) -> str:
        return ""


class _UnusedFetcher:
    def __init__(self) -> None:
        self.calls = 0

    def fetch(self, reference: Reference, revision: str) -> bytes:
        self.calls += 1
        raise AssertionError("nothing may be retrieved for a revision that is refused")
