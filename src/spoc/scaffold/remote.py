"""
Retrieving template sets that live somewhere else.

This is the only module in the kernel that opens an outbound connection, and it
does so only for a reference that explicitly named a remote location.

Two rules here are not obvious from the code they guard, so they are stated:

**Nothing the remote party says is used to build a local path.** Not the
``Content-Disposition`` filename, not the final redirect URL, not a member name
before :mod:`spoc.scaffold.archive` has admitted it. Django's August 2026
advisory was exactly this: a server-supplied filename reached ``os.path.join``
and an absolute path won, writing the archive wherever the attacker chose. There
is no reason a scaffolder needs the server's opinion about a filename, so it
never asks and never reads one.

**A redirect may not weaken what the reference asked for.** ``urllib`` follows
redirects across schemes by default, which would make any transport guarantee
decorative — one hop to ``http://`` and the guarantee is gone without the caller
ever seeing it.
"""

import hashlib
import json
import urllib.error
import urllib.request
from urllib.parse import urlsplit

from .errors import InsecureRedirectError, RetrievalError
from .plan import Reference

#: How long any single request may take. A scaffold is interactive; a stalled
#: connection should fail rather than hang the command.
TIMEOUT_SECONDS = 30

#: The most bytes a single transfer may carry. The expanded-size bound in
#: :mod:`spoc.scaffold.archive` is the one that matters, but refusing an absurd
#: transfer early avoids buffering it in memory first.
MAX_TRANSFER_BYTES = 96 * 1024 * 1024

#: Sent so a rate-limited host can identify the client.
USER_AGENT = "spoc-scaffold"

#: Schemes ordered by the guarantees they carry. A redirect may move within a
#: tier or upward, never downward.
_SECURE_SCHEMES = frozenset({"https"})

#: Hosts that never need TLS to be trustworthy, because the traffic never leaves
#: the machine. Keeps `http://localhost:8000/set.tar.gz` usable while developing
#: a template set without opening a general exemption.
_LOOPBACK_HOSTS = frozenset({"localhost", "127.0.0.1", "::1", "[::1]"})


def _is_secure(url: str) -> bool:
    """True when a URL's guarantees are acceptable as a retrieval destination."""
    parts = urlsplit(url)
    if parts.scheme in _SECURE_SCHEMES:
        return True
    return (parts.hostname or "") in _LOOPBACK_HOSTS


class _NoDowngradeRedirect(urllib.request.HTTPRedirectHandler):
    """Refuses a redirect that lands somewhere weaker than where it started.

    Without this the scheme in a reference is advisory: any host could bounce the
    retrieval onto plaintext and the caller would never know it happened.
    """

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        if _is_secure(req.full_url) and not _is_secure(newurl):
            raise InsecureRedirectError(req.full_url, newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _opener() -> urllib.request.OpenerDirector:
    return urllib.request.build_opener(_NoDowngradeRedirect)


def _get(url: str, reference: Reference, *, accept: str | None = None) -> bytes:
    """Fetch a URL, bounded, reading no path-shaped metadata from the response.

    Failures name the reference the caller supplied, with the URL this adapter
    derived from it as detail. The caller can only correct what they typed —
    reporting `https://api.github.com/repos/o/r/commits/HEAD` to someone who
    wrote `gh:o/r` names something they never chose.
    """
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    if accept:
        request.add_header("Accept", accept)
    try:
        with _opener().open(request, timeout=TIMEOUT_SECONDS) as response:
            # Deliberately bounded read. `Content-Length` is not trusted to size
            # the buffer, and no response header is consulted for anything else —
            # in particular not Content-Disposition, which is how Django's
            # August 2026 arbitrary-write advisory happened.
            payload = response.read(MAX_TRANSFER_BYTES + 1)
    except InsecureRedirectError:
        raise
    except urllib.error.HTTPError as exc:
        raise RetrievalError(
            reference.raw, f"the server answered {exc.code} for {url}"
        ) from exc
    except OSError as exc:
        raise RetrievalError(reference.raw, f"{exc} ({url})") from exc

    if len(payload) > MAX_TRANSFER_BYTES:
        raise RetrievalError(
            reference.raw, f"the transfer exceeds {MAX_TRANSFER_BYTES} bytes"
        )
    return payload


def _github_parts(reference: Reference) -> tuple[str, str]:
    """Split ``gh:owner/repo`` into its two segments."""
    segments = [part for part in reference.location.split("/") if part]
    if len(segments) != 2:
        raise RetrievalError(
            reference.raw, "a gh: reference must name exactly owner/repo"
        )
    return segments[0], segments[1]


class HttpRevisionResolver:
    """Resolves a reference to the exact revision it designates.

    Implements the :class:`~spoc.scaffold.plan.RevisionResolver` port.

    For a ``gh:`` reference this asks the host which commit the named ref points
    at, so a moving reference becomes an immutable one before anything is cached
    or retrieved. For a direct archive URL there is no revision to ask about: the
    URL is the whole identity, so its digest is used as the key and the retrieved
    bytes are what provenance records.
    """

    def resolve(self, reference: Reference) -> str:
        if reference.scheme == "gh":
            owner, repo = _github_parts(reference)
            ref = reference.revision or "HEAD"
            url = f"https://api.github.com/repos/{owner}/{repo}/commits/{ref}"
            payload = _get(url, reference, accept="application/vnd.github+json")
            try:
                sha = json.loads(payload)["sha"]
            except (ValueError, KeyError, TypeError) as exc:
                raise RetrievalError(
                    reference.raw, "the host did not report a revision"
                ) from exc
            return str(sha)

        # A pinned VCS reference already names its revision.
        if reference.revision:
            return reference.revision

        # A direct archive URL carries no revision. Key by the reference itself
        # so the cache is still correct for repeat use of the same URL.
        digest = hashlib.sha256(reference.raw.encode("utf-8")).hexdigest()
        return f"url-{digest[:32]}"


class HttpFetcher:
    """Retrieves the archived content of an exact revision.

    Implements the :class:`~spoc.scaffold.plan.Fetcher` port.
    """

    def fetch(self, reference: Reference, revision: str) -> bytes:
        return _get(self._url_for(reference, revision), reference)

    def _url_for(self, reference: Reference, revision: str) -> str:
        """Build the retrieval URL. Constructed locally, never taken from a
        response, and never from a name the remote party supplied."""
        if reference.scheme == "gh":
            owner, repo = _github_parts(reference)
            return f"https://codeload.github.com/{owner}/{repo}/tar.gz/{revision}"

        if reference.scheme.startswith("git+"):
            transport = reference.scheme.removeprefix("git+")
            base = f"{transport}:{reference.location}".removesuffix(".git")
            return f"{base}/archive/{revision}.tar.gz"

        # A direct archive URL is used as supplied. If it names plaintext, that
        # is the caller's explicit choice and stands; what is refused is being
        # *moved* onto plaintext by a redirect nobody asked for.
        return f"{reference.scheme}:{reference.location}"
