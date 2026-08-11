# API Reference — The Kernel

Everything on this page is importable from `spoc` directly. This is the whole
public surface of the kernel — if it isn't here, a framework author doesn't
need it.

The listing below is derived from the package's own `__all__` at build time —
a new export appears here on the next build, with no edit to this page.

Every error SPOC raises is a subclass of `SpocError`, so one `except` catches
them all — and each one names precisely what failed. For the trigger-and-fix
table, see the [error index](errors.md).

::: spoc
    options:
      show_root_heading: false
