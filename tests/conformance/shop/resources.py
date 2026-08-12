"""A value component: an instance, registered as itself."""

from spoc.core.declaration import component


class SearchIndex:
    def lookup(self, term: str) -> str:
        return term


search_index = component(SearchIndex(), kind="resources", name="search_index")
