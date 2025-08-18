"""Flask application package with a lazily-loaded factory."""

from __future__ import annotations

__all__ = ["create_app", "get_app"]


def create_app(*args, **kwargs):
    """Return a configured :class:`~flask.Flask` application instance."""
    from .app import create_app as _create_app

    return _create_app(*args, **kwargs)


def get_app():
    """Return the module-level Flask application."""
    from .app import app as _app

    return _app
