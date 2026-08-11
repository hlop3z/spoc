"""The storefront's one process-lifetime resource.

The vocabulary's resource recipe, end to end: the component is an *instance*
that knows how to open and close itself; the kind's ``on_startup`` opens it
before any view runs, views reach it through the registry mid-call, and
``on_shutdown`` closes it during teardown. In memory on purpose — the
reference app is about the kernel, not a search engine.
"""

from framework import resource


class SearchIndex:
    """A stand-in for a pool or client: something that must open and close."""

    def __init__(self):
        self.entries = None
        #: The test suite observes the lifecycle here: exactly one "open" on
        #: start, exactly one "close" by the time shutdown returns.
        self.events = []

    def open(self):
        self.events.append("open")
        self.entries = {"keyboard": 1, "mouse": 2}

    def lookup(self, name):
        # A closed index has no entries — a lookup then is simply a miss.
        return (self.entries or {}).get(name)

    def close(self):
        self.events.append("close")
        self.entries = None


# Instances carry no __name__, so a resource states its name explicitly.
search_index = resource(SearchIndex(), name="search_index")
