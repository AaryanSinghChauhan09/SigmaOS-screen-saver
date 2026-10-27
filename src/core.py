"""Lock screen & idle screensaver for SigmaOS-screen-saver (inspired by
cinnamon-screensaver).

Principles: validated idle/lock policy (fail-fast on negative delays), theme
registry, pure status computation, lock rendered as a plan (pure) with a thin
execute layer that self_test never runs against a real session.
"""
import argparse, json, os, subprocess, sys, tempfile

ENGINE = {
    "name": "sigma-screensaver",
    "summary": "Lock screen and idle screensaver policy",
    "language": "python",
    "verbs": ["lock", "idle", "theme", "status"],
    "principles": ["Defensive Programming", "Fail-Fast", "Least Astonishment",
                   "KISS", "Separation of Concerns", "Deterministic Testing"],
}

cli_doc = """\
$ sigma-screensaver lock                 # prints the lock plan (dry-run)
$ sigma-screensaver idle --delay 300 --lock on
$ sigma-screensaver theme --list
$ sigma-screensaver status
"""

DEFAULT_STORE = os.path.expanduser("~/.config/sigma-screensaver/config.json")
THEMES = ("blank", "glitter", "floating", "clock", "ascii")
DEFAULT_CONFIG = {"idle_delay": 300, "lock_on_idle": True,
                  "lock_on_suspend": True, "theme": "blank"}


class SsError(ValueError):
    pass


def validate_config(cfg):
    """Normalise + validate a screensaver config (fail-fast)."""
    out = dict(DEFAULT_CONFIG)
    out.update(cfg or {})
    try:
        delay = int(out["idle_delay"])
    except (TypeError, ValueError):
        raise SsError(f"bad idle_delay: {out['idle_delay']!r}")
    if delay < 0 or delay > 86400:
        raise SsError(f"idle_delay must be 0..86400 seconds, got {delay}")
    if out["theme"] not in THEMES:
        raise SsError(f"unknown theme: {out['theme']!r} (have: {', '.join(THEMES)})")
    return {"idle_delay": delay, "lock_on_idle": bool(out["lock_on_idle"]),
            "lock_on_suspend": bool(out["lock_on_suspend"]), "theme": out["theme"]}


def load_config(path):
    if not os.path.exists(path):
        return dict(DEFAULT_CONFIG)
    with open(path, "r", encoding="utf-8") as fh:
        return validate_config(json.load(fh))  # fail-fast on corrupt store


def save_config(path, cfg):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = path + ".sigma-tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(cfg, fh, indent=2, sort_keys=True)
    os.replace(tmp, path)


def set_idle(cfg, delay, lock=None):
    """Return a NEW config with a validated idle delay (pure)."""
    out = validate_config({**cfg, "idle_delay": delay,
                           **({"lock_on_idle": lock} if lock is not None else {})})
    return out


def set_theme(cfg, theme):
    return validate_config({**cfg, "theme": theme})


def status(cfg):
    """Pure status summary of the current policy."""
    c = validate_config(cfg)
    return {"enabled": c["idle_delay"] > 0, "idle_delay": c["idle_delay"],
            "lock_on_idle": c["lock_on_idle"], "lock_on_suspend": c["lock_on_suspend"],
            "theme": c["theme"],
            "will_lock": c["idle_delay"] > 0 and c["lock_on_idle"]}


def lock_plan(cfg):
    """Pure renderer: config -> the command plan a lock would execute."""
    c = validate_config(cfg)
    cmds = [f"sigma-screensaver-lock --theme {c['theme']}"]
    if c["lock_on_suspend"]:
        cmds.append("loginctl lock-sessions")
    return cmds


def apply_plan(plan, runner=None):
    """Execute layer: run the lock commands against the real session.

    self_test NEVER calls this without an injected (recording) runner.
    """
    if runner is None:
        runner = lambda cmd: subprocess.run(cmd.split(), check=True)
    for cmd in plan:
        runner(cmd)
    return len(plan)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog=ENGINE["name"], description=ENGINE["summary"])
    p.add_argument("--store", default=DEFAULT_STORE, help="config store (JSON)")
    sub = p.add_subparsers(dest="cmd", required=True)
    lk = sub.add_parser("lock", help="render (or apply) the lock plan")
    lk.add_argument("--execute", action="store_true",
                    help="actually lock (requires a live session)")
    idle = sub.add_parser("idle", help="get/set idle policy")
    idle.add_argument("--delay", type=int, default=None,
                      help="idle delay in seconds (0 disables)")
    idle.add_argument("--lock", choices=("on", "off"), default=None)
    th = sub.add_parser("theme", help="get/set/lock the theme")
    th.add_argument("--list", action="store_true", help="list themes")
    th.add_argument("theme", nargs="?", help="theme to set (omit to print current)")
    sub.add_parser("status", help="print the policy status")
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        cfg = load_config(args.store)
        if args.cmd == "lock":
            plan = lock_plan(cfg)
            if args.execute:
                apply_plan(plan)
                print("locked", file=sys.stderr)
            else:
                for cmd in plan:
                    print(cmd)
        elif args.cmd == "idle":
            if args.delay is not None or args.lock is not None:
                cfg = set_idle(cfg, args.delay if args.delay is not None
                               else cfg["idle_delay"],
                               lock={"on": True, "off": False}.get(args.lock))
                save_config(args.store, cfg)
            print(f"idle_delay={cfg['idle_delay']} lock_on_idle="
                  f"{'on' if cfg['lock_on_idle'] else 'off'}")
        elif args.cmd == "theme":
            if args.list:
                for t in THEMES:
                    print(t)
            elif args.theme:
                cfg = set_theme(cfg, args.theme)
                save_config(args.store, cfg)
                print(f"theme = {cfg['theme']}")
            else:
                print(cfg["theme"])
        elif args.cmd == "status":
            st = status(cfg)
            for k in sorted(st):
                print(f"{k} = {st[k]}")
        return 0
    except (SsError, OSError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


def self_test() -> None:
    cfg = dict(DEFAULT_CONFIG)
    # idle policy: validated, fail-fast on negatives / nonsense
    cfg2 = set_idle(cfg, 600, lock=False)
    assert cfg2["idle_delay"] == 600 and cfg2["lock_on_idle"] is False
    assert cfg["idle_delay"] == 300          # original untouched (pure)
    for bad in ({"idle_delay": -1}, {"idle_delay": "soon"},
                {"theme": "disco"}, {"idle_delay": 999999}):
        try:
            validate_config(bad)
        except SsError:
            pass
        else:
            raise AssertionError(f"should reject config {bad}")
    # status (pure, deterministic)
    st = status(cfg)
    assert st == {"enabled": True, "idle_delay": 300, "lock_on_idle": True,
                  "lock_on_suspend": True, "theme": "blank", "will_lock": True}
    off = set_idle(cfg, 0)
    assert status(off)["will_lock"] is False and status(off)["enabled"] is False
    # theme switching + lock plan rendering
    cfg3 = set_theme(cfg, "clock")
    assert lock_plan(cfg3) == ["sigma-screensaver-lock --theme clock",
                               "loginctl lock-sessions"]
    no_suspend = validate_config({**cfg3, "lock_on_suspend": False})
    assert lock_plan(no_suspend) == ["sigma-screensaver-lock --theme clock"]
    # execute layer uses an injected (recording) runner
    seen = []
    assert apply_plan(lock_plan(cfg3), runner=seen.append) == 2
    assert seen[0] == "sigma-screensaver-lock --theme clock"
    # persistence round-trip (tempdir only)
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "config.json")
        save_config(path, cfg3)
        assert load_config(path) == cfg3
        assert load_config(os.path.join(d, "none.json")) == DEFAULT_CONFIG
        with open(path, "w", encoding="utf-8") as fh:
            fh.write('{"idle_delay": -5}')
        try:
            load_config(path)
        except SsError:
            pass
        else:
            raise AssertionError("corrupt store not caught")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
