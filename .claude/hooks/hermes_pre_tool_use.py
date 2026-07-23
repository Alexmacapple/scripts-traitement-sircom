#!/usr/bin/env python3
"""Generated Claude Code PreToolUse hook for a child Hermes pack.

Defense-in-depth only: Claude Code project hooks can be disabled, malformed, or
fail open. This hook denies only what it can confidently parse before a tool
call lands; the deterministic observer and veto-only judge remain the source of
truth for every merge decision.

What it reads in a Bash command: shell redirections AND the commands that write by
themselves (`python -c open(...)`, `tee`, `sed -i`, `cp`, `mv`, `dd`, `install`,
`truncate`, `touch`, `ln`, and a `sh -c` payload, recursively). It used to read
redirections only, which meant the write surface held against Write/Edit and was walked
around by any of the above (third opinion 2026-07-12, Exp. A).

The honest limit, stated where the promise is made (README, "Honnête, tout de suite"):
a shell parser is NEVER complete. `python -c "open('sec' + 'rets.env', 'w')"`, a path
computed at runtime, an exotic interpreter — this hook does not see them. It is a
corridor that closes the forms an agent actually emits, not a sandbox. The control that
does not depend on parsing anything is the observer: it recomputes the real git diff and
refuses whatever landed outside the route.
"""
from __future__ import annotations

import fnmatch
import json
import os
import re
import shlex
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover - exercised by the fail-closed tests.
    # NOT fail-open. Without PyYAML the route map cannot be read, so the write surface is
    # unknown — and an unknown surface used to mean NO check at all, in silence: on a
    # machine that never installed the dependency the corridor simply did not exist and
    # nothing said so (P3). A security control does not disappear because a dependency is
    # missing. It refuses (below, in decide()) and it says so (_shout_missing_yaml).
    yaml = None


# MUST mirror runtime/governance.py GOVERNANCE_RELS and GOVERNANCE_GLOBS.
GOVERNANCE_RELS = (
    ".hermes/control/mutation-policy.yml",
    ".hermes/control/operating-envelope.yml",
    ".hermes/control/tool-policy.yml",
    ".hermes/control/oracles.yml",
    ".hermes/control/skills-lock.yml",
    ".hermes/control/engine-plan.yml",
    ".hermes/control/behavior-contract.yml",
    ".hermes/control/disclosure-map.yml",
    ".hermes/control/task-router.yml",
    ".hermes/control/gates.yml",
    ".hermes/control/owners.yml",
    ".hermes/control/allowed-signers",
    ".hermes/control/production-target.yml",
    ".claude/settings.json",
    ".claude/hooks/hermes_pre_tool_use.py",
)
GOVERNANCE_GLOBS = (".hermes/control/confirmation-signatures/*",)

_V4A_FILE = re.compile(r"^\*\*\*\s*(?:Update|Add|Delete)\s+File:\s*(.+?)\s*$")
_V4A_MOVE = re.compile(r"^\*\*\*\s*Move\s+File:\s*(.+?)\s*->\s*(.+?)\s*$")
_GIT_HDR = re.compile(r'^diff --git "?a/(.+?)"?\s+"?b/(.+?)"?\s*$')
_UNI_HDR = re.compile(r"^(?:\+\+\+|---)\s+(.+?)\s*$")
_REDIR = re.compile(r"^(?:[0-9]*>\||[0-9]*>>?|&>)(.+)$")
_PATH_KEYS = (
    "path", "file_path", "filepath", "filename", "file_name", "file",
    "target_file", "dest", "destination", "output_path", "notebook_path",
)
_PATCH_KEYS = ("patch", "diff", "input")
_COMMAND_TOOL_NAMES = {"Bash", "Shell", "shell", "bash"}
_ACTIVE_ROUTE_REL = ".hermes/active-route"

# Command writes (third opinion 2026-07-12, Exp. A): a corridor that reads only shell
# redirections is walked around by every command that writes by itself.
_SHELL_SEPARATORS = {";", "|", "||", "&", "&&", "\n"}
_REDIRECT_OPS = {">", ">>", ">|", "1>", "1>>", "2>", "2>>", "&>"}
_PY_INTERPRETERS = {"python", "python2", "python3", "py"}
_SHELLS = {"sh", "bash", "zsh", "dash", "ksh"}
_MAX_SHELL_DEPTH = 3
_WRITE_MODE = r"[^'\"]*[waxWAX+][^'\"]*"
_PY_OPEN_WRITE = re.compile(
    r"""open\(\s*(?P<q>['"])(?P<path>[^'"]+)(?P=q)\s*,\s*['"]%s['"]""" % _WRITE_MODE)
_PY_PATH_WRITE = re.compile(
    r"""Path\(\s*(?P<q>['"])(?P<path>[^'"]+)(?P=q)\s*\)\s*\.\s*"""
    r"""(?:write_text|write_bytes|touch|mkdir|open\(\s*['"]%s['"])""" % _WRITE_MODE)
_PY_OS_OPEN_WRITE = re.compile(
    r"""os\.open\(\s*(?P<q>['"])(?P<path>[^'"]+)(?P=q)\s*,[^)]*O_(?:WRONLY|RDWR|CREAT|APPEND)""")


def _deny(reason):
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }


def _unquote(text):
    if len(text) >= 2 and text[0] == '"' and text[-1] == '"':
        try:
            return text[1:-1].encode("latin-1").decode("unicode_escape")
        except Exception:  # noqa: BLE001
            return text[1:-1]
    return text


def _strip_ab(path):
    return path[2:] if path.startswith(("a/", "b/")) else path


def _diff_targets(text):
    lines = [line.rstrip() for line in text.splitlines()]
    is_v4a = any(
        _V4A_FILE.match(line)
        or _V4A_MOVE.match(line)
        or line.strip() in ("*** Begin Patch", "***Begin Patch")
        for line in lines
    )
    out = []
    for line in lines:
        m = _V4A_MOVE.match(line)
        if m:
            out.append(m.group(1).strip())
            out.append(m.group(2).strip())
            continue
        m = _V4A_FILE.match(line)
        if m:
            out.append(m.group(1).strip())
            continue
        if is_v4a:
            continue
        m = _GIT_HDR.match(line)
        if m:
            out.append(_strip_ab(_unquote(m.group(1).strip())))
            out.append(_strip_ab(_unquote(m.group(2).strip())))
            continue
        m = _UNI_HDR.match(line)
        if m:
            cand = _unquote(m.group(1).strip().split("\t", 1)[0])
            if cand and cand != "/dev/null":
                out.append(_strip_ab(cand))
    return out


def _command_redirect_targets(command):
    try:
        tokens = shlex.split(command)
    except ValueError:
        return []
    out = []
    for idx, token in enumerate(tokens):
        if token in {">", ">>", "1>", "1>>", "2>", "2>>", "&>", ">|"}:
            if idx + 1 < len(tokens):
                out.append(tokens[idx + 1])
            continue
        m = _REDIR.match(token)
        if m and m.group(1):
            out.append(m.group(1))
    return [item for item in out if item and item not in {"-", "/dev/null"}]


def _shell_segments(command):
    """Simple-command segments of a command line, quote-aware.

    punctuation_chars makes the lexer emit `;`, `|`, `&&`, `||`, `>` as their own tokens
    while leaving quoted code (`python -c "a;b"`) intact — a naive split on `;` would cut
    a `-c` payload in half.
    """
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
        lexer.whitespace_split = True
        tokens = list(lexer)
    except ValueError:
        return []
    segments, current = [], []
    for token in tokens:
        if token in _SHELL_SEPARATORS:
            if current:
                segments.append(current)
            current = []
        elif token in _REDIRECT_OPS:
            # Redirections are _command_redirect_targets' job; drop the operator and its
            # target so `cp a > b` does not read `b` as cp's destination as well.
            if current:
                segments.append(current)
            current = [None]  # poison: skip the redirect target, keep segment boundaries
        elif current == [None]:
            current = []
        else:
            current.append(token)
    if current and current != [None]:
        segments.append(current)
    return [seg for seg in segments if seg and seg != [None]]


def _positional_args(args, value_flags=()):
    """Args that are not flags, skipping the value of any flag that takes one."""
    out = []
    skip = False
    for arg in args:
        if skip:
            skip = False
            continue
        if arg.startswith("-") and arg != "-":
            if arg in value_flags:
                skip = True
            continue
        out.append(arg)
    return out


def _python_write_targets(code):
    """Paths a `python -c` payload writes to, for the forms we can read with confidence.

    A regex is not a Python parser: `open('sec' + 'rets.env', 'w')` is invisible to it, and
    so is anything computed at runtime. That is stated where the promise is made (README,
    module docstring) — the deterministic observer, not this hook, is the control. What this
    closes is the SILENT walk-around: the plain forms an agent actually emits.
    """
    out = []
    for rx in (_PY_OPEN_WRITE, _PY_PATH_WRITE, _PY_OS_OPEN_WRITE):
        out.extend(m.group("path") for m in rx.finditer(code))
    return out


def _segment_write_targets(segment, depth):
    if not segment:
        return []
    name = os.path.basename(segment[0])
    args = segment[1:]

    if name in _PY_INTERPRETERS:
        return [t for idx, tok in enumerate(args) if tok == "-c" and idx + 1 < len(args)
                for t in _python_write_targets(args[idx + 1])]
    if name in _SHELLS and depth < _MAX_SHELL_DEPTH:
        out = []
        for idx, tok in enumerate(args):
            if tok == "-c" and idx + 1 < len(args):
                out.extend(_command_write_targets(args[idx + 1], depth + 1))
        return out
    if name == "dd":
        return [tok[3:] for tok in args if tok.startswith("of=") and len(tok) > 3]
    if name == "sed":
        if not any(a == "--in-place" or (a.startswith("-i") and not a.startswith("--")) for a in args):
            return []
        positional = _positional_args(args, value_flags=("-e", "-f", "--expression", "--file"))
        scripted = any(a in ("-e", "-f", "--expression", "--file")
                       or a.startswith(("--expression=", "--file="))
                       for a in args)
        # Without -e/-f the first positional IS the sed script, not a file.
        return positional if scripted else positional[1:]
    if name == "tee":
        return _positional_args(args)
    if name == "touch":
        return _positional_args(args, value_flags=("-d", "-r", "-t", "--date", "--reference"))
    if name == "truncate":
        return _positional_args(args, value_flags=("-s", "-r", "--size", "--reference"))
    if name in ("cp", "mv", "install", "ln", "rsync"):
        value_flags = ("-m", "-o", "-g", "-S", "--mode", "--owner", "--group", "--suffix")
        for idx, tok in enumerate(args):
            if tok == "-t" or tok == "--target-directory":
                return [args[idx + 1]] if idx + 1 < len(args) else []
            if tok.startswith("--target-directory="):
                return [tok.split("=", 1)[1]]
        positional = _positional_args(args, value_flags=value_flags)
        # The destination is the last positional; a lone one (`cp a`) writes nothing.
        return positional[-1:] if len(positional) >= 2 else []
    return []


def _command_write_targets(command, depth=0):
    """Paths a Bash command writes to: shell redirections PLUS commands that write by
    themselves.

    The corridor used to read redirections only (`>`, `>>`, `2>`…), so it held against the
    Write/Edit tools and was walked around by any command that writes on its own:
    `Write secrets.env` denied, `Bash: python -c "open('secrets.env','w')"` allowed — and a
    gitignored path written that way enters no diff, so the observer does not catch it
    either (third opinion 2026-07-12, Exp. A).
    """
    out = list(_command_redirect_targets(command)) if depth == 0 else []
    for segment in _shell_segments(command):
        out.extend(_segment_write_targets(segment, depth))
    return [item for item in out if item and item not in {"-", "/dev/null"}]


def _extract_targets(payload):
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        return []
    targets = []
    for key in _PATH_KEYS:
        value = tool_input.get(key)
        if isinstance(value, str) and value.strip():
            targets.append(value)
        elif isinstance(value, list):
            targets.extend(item for item in value if isinstance(item, str) and item.strip())
    for key in _PATCH_KEYS:
        value = tool_input.get(key)
        if isinstance(value, str) and (
            "***" in value or "+++" in value or "---" in value or "diff --git" in value
        ):
            targets.extend(_diff_targets(value))
    command = tool_input.get("command")
    if isinstance(command, str) and payload.get("tool_name") in _COMMAND_TOOL_NAMES:
        targets.extend(_command_write_targets(command))
    seen = set()
    out = []
    for target in targets:
        if target not in seen:
            seen.add(target)
            out.append(target)
    return out


def _safe_yaml(path):
    if yaml is None:
        return None
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, yaml.YAMLError):
        return None


def _load_owners_sealed(poc):
    doc = _safe_yaml(poc / ".hermes/control/owners.yml")
    sealed = doc.get("sealed") if isinstance(doc, dict) else None
    if not isinstance(sealed, list):
        return []
    return [item for item in sealed if isinstance(item, str) and item]


def _active_route(payload, poc):
    for value in (
        os.environ.get("HERMES_ACTIVE_ROUTE"),
        os.environ.get("PDHB_ACTIVE_ROUTE"),
        payload.get("route"),
        payload.get("active_route"),
        payload.get("hermes_route"),
    ):
        if isinstance(value, str) and value.strip():
            return value.strip()
    try:
        value = (poc / _ACTIVE_ROUTE_REL).read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return value or None


def _route_paths(route):
    allowed = route.get("allowed_paths") or []
    if not isinstance(allowed, list):
        return None
    return [p for p in allowed if isinstance(p, str) and p]


def _write_surface(poc, route_id):
    """(surface, problem) — the paths a write may land on right now.

    With an active route, the surface is THAT route's allowed_paths. Without one,
    it is the UNION of every declared route's allowed_paths: no route is selected,
    so the hook cannot say which lane a write belongs to, but it can still say the
    write left the harness entirely. The union is the weaker of the two checks and
    the observer still enforces the per-route surface afterwards — but it is never
    the empty check. `.hermes/active-route` is written by nothing today, so a routeless
    session used to skip the path check ALTOGETHER and allow any write in the PoC.

    Returns surface=None (no path check) only when the map declares no surface at all — a
    pack with no route is already invalid, and validate_pack is the gate for that, not this
    hook. An UNREADABLE map is a different case and no longer reaches here: decide() refuses
    the call outright when PyYAML is missing (P3 — it used to allow every write in silence).
    """
    doc = _safe_yaml(poc / ".hermes/control/disclosure-map.yml")
    if not isinstance(doc, dict):
        return None, None
    routes = [r for r in (doc.get("routes") or []) if isinstance(r, dict)]
    if route_id:
        for route in routes:
            if route.get("id") == route_id:
                allowed = _route_paths(route)
                if allowed is None:
                    return [], "active route %s has malformed allowed_paths" % route_id
                return allowed, None
        return [], "active route %s is not declared in disclosure-map.yml" % route_id
    union = []
    for route in routes:
        for path in _route_paths(route) or []:
            if path not in union:
                union.append(path)
    return (sorted(union) or None), None


def _harness_owned(rel):
    """Harness bookkeeping, not PoC product code: routes never enumerate it.

    The child writes its own memory here, and the sealed subset is already denied by
    _is_governance. The write surface governs the PoC's sources; applying it to these
    paths would deny a child its own `.hermes/memory/` — a different rule, not this one.

    `.hermes-operator-artifacts/` is the same idea, learned the hard way. The operator
    runs the JUDGE as a CLI with `cwd = the PoC` (engines.run_judge), exactly like the
    worker — so the judge loads this very hook, and the write corridor built to bound a
    WORKER denied the judge its own `verdict.json`, which lives there. The engine
    returned nothing, and the veto-only judge — the half of the product where a second
    model hunts for the flaw — could never run at all (first real production run,
    2026-07-13).

    This grants a worker NOTHING it could use: the operator git-EXCLUDES that directory
    (`cycle.py`: "ignored files never enter the worker-diff surface"), so the observer
    re-derives the diff from git and never sees a byte written there — nothing put in it
    can reach a merge. Governance-core stays denied above, independently.
    """
    return rel.startswith((".hermes/", ".claude/", ".agents/",
                           ".hermes-operator-artifacts/"))


def _matches(rel, globs):
    return any(rel == glob or fnmatch.fnmatch(rel, glob) for glob in globs)


def _sealed(rel, owners):
    return rel in GOVERNANCE_RELS or _matches(rel, GOVERNANCE_GLOBS) or _matches(rel, owners)


def _is_governance(rel, poc_lex, owners):
    if _sealed(rel, owners):
        return True
    try:
        real = os.path.realpath(os.path.join(poc_lex, rel.replace("/", os.sep)))
        real_rel = os.path.relpath(real, os.path.realpath(poc_lex)).replace(os.sep, "/")
    except (ValueError, OSError):
        return False
    if real_rel == ".." or real_rel.startswith("../"):
        return False
    return _sealed(real_rel, owners)


def _rel_for_target(raw, poc_lex, cwd):
    if "\x00" in raw:
        raise ValueError("NUL byte in path")
    full = raw if os.path.isabs(raw) else os.path.join(
        cwd if isinstance(cwd, str) and cwd else poc_lex,
        raw,
    )
    norm = os.path.abspath(full)
    rel = os.path.relpath(norm, poc_lex)
    if rel == os.pardir or rel.startswith(os.pardir + os.sep) or os.path.isabs(rel):
        return None
    return rel.replace(os.sep, "/")


def _tool_policy_forbidden(poc):
    doc = _safe_yaml(poc / ".hermes/control/tool-policy.yml")
    items = doc.get("forbidden") if isinstance(doc, dict) else None
    if not isinstance(items, list):
        return []
    return [item for item in items if isinstance(item, str) and item.strip()]


def _norm_text(text):
    return " ".join(str(text).replace("-", " ").replace("_", " ").lower().split())


def _forbidden_command_reason(payload, poc):
    if payload.get("tool_name") not in _COMMAND_TOOL_NAMES:
        return None
    tool_input = payload.get("tool_input")
    command = tool_input.get("command") if isinstance(tool_input, dict) else None
    if not isinstance(command, str) or not command.strip():
        return None
    haystack = _norm_text(command)
    for item in _tool_policy_forbidden(poc):
        needle = _norm_text(item)
        if needle and needle in haystack:
            return "forbidden command from tool-policy.yml: %s" % item
    return None


_NO_YAML_REASON = (
    "PyYAML is missing, so .hermes/control/*.yml cannot be read: the route map, the write "
    "surface and the tool policy are all unknown. This hook refuses the call rather than "
    "let a write through unchecked (it used to allow every write, silently). Install it "
    "(`pip install pyyaml`) — the observer and the pack validator need it too."
)


def _shout_missing_yaml():
    """Never silent: a degraded machine must not look like a healthy one.

    A call that writes nothing is still allowed (otherwise `pip install pyyaml` — the fix —
    would itself be blocked, and fail-closed would become a trap), but the degradation is
    announced on every invocation."""
    sys.stderr.write(
        "hermes hook: PyYAML is missing; the write-surface check is INACTIVE and every "
        "write will be refused. Install pyyaml.\n")


def decide(payload, poc):
    if not isinstance(payload, dict):
        return None
    poc = Path(poc)
    poc_lex = os.path.abspath(str(poc))

    reason = _forbidden_command_reason(payload, poc)
    if reason:
        return _deny(reason)

    targets = _extract_targets(payload)
    if not targets:
        if yaml is None:
            _shout_missing_yaml()
        return None

    if yaml is None:
        # Fail-closed. _write_surface would return None here (map unreadable), and a None
        # surface skips the path check entirely — which is exactly the hole: no dependency,
        # no gate, no warning.
        _shout_missing_yaml()
        return _deny(_NO_YAML_REASON)

    route_id = _active_route(payload, poc)
    allowed, route_problem = _write_surface(poc, route_id)
    if route_problem:
        return _deny(route_problem)

    owners = _load_owners_sealed(poc)
    cwd = payload.get("cwd")
    for raw in targets:
        rel = _rel_for_target(raw, poc_lex, cwd)
        if rel is None:
            return _deny("write outside the PoC (%s) is never in a route" % raw)
        if _is_governance(rel, poc_lex, owners):
            return _deny(
                "governance-core/sealed file %s changes only out-of-band "
                "(human approval), never a worker write" % rel
            )
        if allowed is None or _harness_owned(rel):
            continue
        if not _matches(rel, allowed):
            if route_id:
                return _deny(
                    "%s is outside active route %s allowed_paths; this write leaves "
                    "the harness lane" % (rel, route_id)
                )
            return _deny(
                "%s is outside the allowed_paths of every declared route; this write "
                "leaves the harness lane (no active route is selected, so the union of "
                "all route surfaces applies)" % rel
            )
    return None


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    root = argv[0] if argv else os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError, OSError):
        return 0
    try:
        verdict = decide(payload, root)
    except Exception:  # noqa: BLE001 - fail open; observer/judge remain authoritative.
        return 0
    if verdict is not None:
        sys.stdout.write(json.dumps(verdict, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
