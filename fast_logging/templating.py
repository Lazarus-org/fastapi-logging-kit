"""Jinja2 templating for ``fast_logging``.

``django_logging`` rendered its email and LogiBoard templates through
``django.template.engines["django"]``. FastAPI has no template engine of
its own, so ``fast_logging`` ships a small Jinja2 environment rooted at
the package's ``templates/`` directory.

The Django template syntax used by the ported templates (``{{ var }}``
and ``{% if %}``/``{% endif %}``) is valid Jinja2, so the templates carry
over essentially unchanged; only ``{% static %}`` tags are rewritten to
use the :func:`static_url` global.

"""

import os
from typing import Any, Dict, Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape

# Absolute paths to the packaged templates and static assets.
PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(PACKAGE_DIR, "templates")
STATIC_DIR = os.path.join(PACKAGE_DIR, "static")

# The URL prefix the static assets are mounted under. Kept in sync with
# fast_logging.routers.log_iboard when the router is attached to an app.
STATIC_URL_PREFIX = "/fast-logging/static"


def static_url(path: str) -> str:
    """Return the URL for a packaged static asset.

    This is the Jinja2 replacement for Django's ``{% static %}`` tag.

    Args:
        path (str): The asset path relative to the static directory,
            e.g. ``LogiBoard/css/app.css``.

    Returns:
        str: The absolute URL the asset is served from.

    """
    return f"{STATIC_URL_PREFIX}/{path.lstrip('/')}"


def _build_environment() -> Environment:
    """Create the Jinja2 environment used to render packaged templates.

    Returns:
        Environment: A configured Jinja2 environment.

    """
    env = Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        autoescape=select_autoescape(["html", "xml"]),
    )
    env.globals["static"] = static_url
    return env


environment: Environment = _build_environment()


def render_to_string(
    template_name: str, context: Optional[Dict[str, Any]] = None
) -> str:
    """Render a packaged template to a string.

    Args:
        template_name (str): The template file name, e.g.
            ``email_notifier_template.html``.
        context (Optional[Dict[str, Any]]): The rendering context.

    Returns:
        str: The rendered template.

    """
    template = environment.get_template(template_name)
    return template.render(**(context or {}))
