import os
import sys
from pathlib import Path

import click


REQUIRED_BY_SCOPE: dict[str, tuple[str, ...]] = {
    "places": ("GOOGLE_MAPS_API_KEY",),
    "llm":    ("LLM_API_KEY",),
}


def missing_keys(scope: str) -> list[str]:
    needed = REQUIRED_BY_SCOPE.get(scope, ())
    return [k for k in needed if not os.getenv(k)]


def _append_to_env(path: Path, values: dict[str, str]) -> None:
    existing = ""
    if path.exists():
        existing = path.read_text(encoding="utf-8")
        if existing and not existing.endswith("\n"):
            existing += "\n"
    new_lines = [f"{k}={v}" for k, v in values.items()]
    path.write_text(existing + "\n".join(new_lines) + "\n", encoding="utf-8")


def run_wizard(*scopes: str, env_path: Path | None = None) -> bool:
    """Prompt for any missing keys across the given scopes; write them to
    .env in cwd; instruct the user to re-run. Returns True iff anything was
    collected and written. No-op (returns False) in non-tty sessions."""
    if not sys.stdin.isatty():
        return False
    needed: list[str] = []
    for scope in scopes:
        for k in missing_keys(scope):
            if k not in needed:
                needed.append(k)
    if not needed:
        return False
    target = env_path if env_path is not None else Path.cwd() / ".env"
    click.echo("Some required keys are not set. Let's collect them now.")
    click.echo(f"They will be appended to {target} (you can edit this file later).")
    values: dict[str, str] = {}
    for key in needed:
        entered = click.prompt(f"  {key}", default="", show_default=False, hide_input=True)
        if entered and entered.strip():
            values[key] = entered.strip()
    if not values:
        click.echo("No values entered. Set the variables manually and re-run.", err=True)
        return False
    _append_to_env(target, values)
    click.echo(f"Wrote {len(values)} key(s) to {target}.")
    click.echo("Please re-run the command so the new values are loaded.")
    return True
