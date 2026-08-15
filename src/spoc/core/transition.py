"""
The window a lifecycle transition holds open, and who is inside it.

A transition — a start or a shutdown — is serialized against every other one and
is a window with an inside and an outside. Work the transition itself invokes is
inside: its hooks, the module code they run, anything those call in turn. Every
other caller is outside. The distinction is the whole reason this module exists,
because the two refusals it drives have opposite remedies. A caller refused for
*reentrancy* invoked a transition from within one and can never retry. A caller
refused for a *busy* framework merely arrived during someone else's transition
and may retry once it settles. Answering either with the other's error argues the
caller out of the fix that would work.

Kept apart from the framework because the argument here is entirely about
concurrency and holds no opinion about what a framework is: three pieces of state
— a lock, the label of whatever is in flight, and a per-context membership marker
— and the rules for reading and writing them together.
"""

from __future__ import annotations

import contextvars
import threading
from collections.abc import Iterator
from contextlib import contextmanager

from .exceptions import FrameworkTransitioningError, SpocError

#: Raised when a transition arrives while another already holds the framework.
#: One definition because both lifecycle paths report it and a caller may be
#: matching on the wording; two spellings of one condition is the drift a single
#: message exists to prevent.
_ALREADY_IN_PROGRESS = "Framework lifecycle transition already in progress"

#: The gates whose transition the current thread or task is *inside* — the
#: transition's own hooks, module code, and anything they call.
#:
#: A ``ContextVar`` rather than thread state, because one mechanism has to answer
#: for both lifecycle paths and its isolation rules already match them: a new
#: thread starts with an empty context, so a racing caller on another thread is
#: outside; a task carries the context copied when it was created, so a task that
#: predates the transition is outside while the transition's own inline awaits are
#: inside. Work a hook spawns inherits the marker, which is intended — work
#: spawned by teardown is teardown. That inheritance follows the context, not the
#: spawning: a task and `asyncio.to_thread` both copy it, a bare `threading.Thread`
#: does not and is therefore outside, as it was under every earlier discriminator.
#:
#: This one marker answers membership for every refusal — a read, and a further
#: lifecycle transition alike. Thread identity cannot: on the asynchronous path a
#: racing task shares the transition's thread while carrying none of its context,
#: so it would be called reentrant for running on the same event loop.
#:
#: A set, not a flag: nesting is per gate, so one framework's startup hook may
#: legally start another, and a read on the outer one stays inside its own
#: transition while the inner one runs.
_active_transitions: contextvars.ContextVar[frozenset[TransitionGate]] = (
    contextvars.ContextVar("spoc_active_transitions", default=frozenset())
)


class TransitionGate:
    """Serializes one framework's lifecycle transitions and marks their window.

    One gate belongs to one framework and is built in its constructor. Membership
    is keyed by the gate rather than by the framework that owns it, which is what
    lets this module stand alone; because the relationship is one-to-one, that
    changes nothing about who counts as inside.
    """

    __slots__ = ("_label", "_lock")

    def __init__(self) -> None:
        self._lock = threading.Lock()
        #: The label of the transition in flight, or ``None`` when settled.
        #: Answers *whether* a transition is running; `_active_transitions`
        #: answers *who is inside it*, which is a different question.
        self._label: str | None = None

    @property
    def inside(self) -> bool:
        """Whether the calling code is part of this gate's in-flight transition."""
        return self in _active_transitions.get()

    def refuse_reentry(self, label: str) -> None:
        """Refuse a transition called from inside one already in flight.

        Membership is the same question a read asks, so it gets the same answer:
        `inside`. Deciding it by thread identity instead would call a racing task
        reentrant merely for sharing an event loop, and the two have opposite
        remedies. Callers this returns for fall through to the lock, which is what
        reports a genuinely concurrent transition.
        """
        if self.inside:
            raise SpocError(
                f"{label} was called from inside a lifecycle transition that is "
                "still in flight. A ready callback, lifecycle hook, or module "
                "initializer cannot start or shut down the framework that is "
                "booting it"
            )

    def refuse_racing_read(self, identifier: str) -> None:
        """Refuse a read that arrived from outside an in-flight transition.

        Checked here rather than inside the registry: the registry is a pure store
        with no notion of a lifecycle, and this gate is what owns the transition.
        During one, the store is being populated app by app, or has already been
        replaced — so an unrefused read either reports a typo the caller did not
        make or hands back a component whose teardown has run.
        """
        label = self._label
        if label is not None and not self.inside:
            raise FrameworkTransitioningError(identifier, label)

    @contextmanager
    def hold(self, label: str) -> Iterator[None]:
        """Take the lock, waiting for it if another transition holds it.

        The synchronous lifecycle path. Waiting is safe here because the caller is
        a thread that has nothing else to do; on the asynchronous path it is not,
        which is what `claim` exists for.
        """
        self.refuse_reentry(label)
        with self._lock, self._window(label):
            yield

    @contextmanager
    def claim(self, label: str) -> Iterator[None]:
        """Take the lock or refuse immediately; never wait for it.

        The asynchronous lifecycle path. Waiting would park the caller's event
        loop, and worse, the transition being waited for may be running on that
        same loop — in which case waiting could never let it finish. Refusing is
        also the honest answer: a concurrent caller may retry once the transition
        settles, so it is given the chance to decide when.
        """
        self.refuse_reentry(label)
        if not self._lock.acquire(blocking=False):
            raise SpocError(_ALREADY_IN_PROGRESS)
        try:
            with self._window(label):
                yield
        finally:
            self._lock.release()

    @contextmanager
    def _window(self, label: str) -> Iterator[None]:
        """Mark the transition in flight and this context as inside it, then unmark.

        Written once because both entry points need it, and a path that marked one
        half would either refuse the transition's own teardown reads or refuse
        nobody's. The context variable is reset by token rather than re-set to a
        computed value: restoring the previous set is what makes nesting unwind
        correctly, and a leaked marker would exempt every later read on this thread
        or task and make every later transition on it look reentrant.
        """
        self._label = label
        token = _active_transitions.set(_active_transitions.get() | {self})
        try:
            yield
        finally:
            _active_transitions.reset(token)
            self._label = None
