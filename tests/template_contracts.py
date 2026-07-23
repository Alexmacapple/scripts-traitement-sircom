from __future__ import annotations

import re
from pathlib import Path

from jinja2 import Environment, FileSystemLoader


TEMPLATE_ROOT = Path(__file__).resolve().parents[1] / "sircom2026" / "templates"
_INCLUDE_RE = re.compile(r'{%\s*include\s+(["\'])(?P<name>[^"\']+)\1\s*%}')
_ENV = Environment(loader=FileSystemLoader(TEMPLATE_ROOT))


def read_template_with_includes(
    template: str | Path, _stack: tuple[str, ...] = ()
) -> str:
    source, template_name = _load_template_source(template)
    if template_name in _stack:
        cycle = " -> ".join((*_stack, template_name))
        raise RecursionError(f"Recursive template include detected: {cycle}")

    stack = (*_stack, template_name)
    return _INCLUDE_RE.sub(
        lambda match: read_template_with_includes(match.group("name"), stack),
        source,
    )


def _load_template_source(template: str | Path) -> tuple[str, str]:
    template_name = _template_name(template)
    source, _filename, _uptodate = _ENV.loader.get_source(_ENV, template_name)
    return source, template_name


def _template_name(template: str | Path) -> str:
    if isinstance(template, str):
        return template
    if template.is_absolute():
        return template.relative_to(TEMPLATE_ROOT).as_posix()
    return template.as_posix()
