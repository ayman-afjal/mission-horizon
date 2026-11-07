"""Tiny mission-script language. No eval: hand-written recursive-descent expressions.

Commands:
  throttle <expr>            set throttle 0..1
  throttle <expr> until <cond>   keep re-evaluating <expr> every step until <cond> (closed-loop control;
                             also works for pitch)
  pitch <expr>               attitude, degrees above the local horizon (90 = up), heading east
  sas hold|prograde|retrograde|radial_out|radial_in
  stage                      drop the bottom stage
  wait <expr>                wait N seconds
  wait until <cond>          block until condition is true
  warp <n>                   request time warp (1,2,4,10,50,100,1000,10000,100000)
  print <text>               message to the flight log
  if <cond> then <command>   conditional one-liner
  end                        stop the script
Numbers accept suffixes: km, min, h.   Functions: sqrt() abs() min(a,b) max(a,b).   Comments start with #.
Variables: altitude apoapsis periapsis speed vertical_speed horizontal_speed eta_apoapsis
           eta_periapsis mission_time throttle stage_fuel mass stages twr thrust q eccentricity
           moon_angle (deg, Moon ahead of you along your orbit)  moon_distance  in_moon_soi (1 inside Moon's sphere of influence)
"""
import re

FUNCS = {"sqrt": 1, "abs": 1, "min": 2, "max": 2}
VARS = {"altitude", "apoapsis", "periapsis", "speed", "vertical_speed", "horizontal_speed",
        "eta_apoapsis", "eta_periapsis", "mission_time", "throttle", "stage_fuel", "mass",
        "stages", "twr", "thrust", "q", "eccentricity", "moon_angle", "moon_distance", "in_moon_soi", "gravity", "landed"}
SAS_MODES = {"hold", "prograde", "retrograde", "radial_out", "radial_in"}
TOKEN = re.compile(r"\s*(?:(\d+\.?\d*(?:e[+-]?\d+)?)(km|min|h)?|([A-Za-z_]\w*)|(>=|<=|==|!=|[><+\-*/(),]))", re.I)

class ParseError(Exception):
    def __init__(self, line, msg): super().__init__(f"line {line}: {msg}"); self.line = line; self.msg = msg

def tokenize(s, line):
    toks, pos = [], 0
    s = s.rstrip()
    while pos < len(s):
        m = TOKEN.match(s, pos)
        if not m or m.end() == pos: raise ParseError(line, f"unexpected character '{s[pos:].strip()[:1]}'")
        pos = m.end()
        if m.group(1) is not None:
            v = float(m.group(1)); u = (m.group(2) or "").lower()
            v *= {"km": 1000.0, "min": 60.0, "h": 3600.0, "": 1.0}[u]
            toks.append(("num", v))
        elif m.group(3): toks.append(("name", m.group(3).lower()))
        else: toks.append(("op", m.group(4)))
    return toks

class Expr:
    """Parsed expression tree as nested tuples."""

class P:
    def __init__(self, toks, line): self.t = toks; self.i = 0; self.line = line
    def peek(self): return self.t[self.i] if self.i < len(self.t) else None
    def take(self): v = self.peek(); self.i += 1; return v
    def err(self, m): raise ParseError(self.line, m)
    def expr(self):
        n = self.term()
        while self.peek() in (("op", "+"), ("op", "-")):
            op = self.take()[1]; n = (op, n, self.term())
        return n
    def term(self):
        n = self.factor()
        while self.peek() in (("op", "*"), ("op", "/")):
            op = self.take()[1]; n = (op, n, self.factor())
        return n
    def factor(self):
        t = self.take()
        if t is None: self.err("expression expected")
        if t[0] == "num": return ("num", t[1])
        if t[0] == "name" and t[1] in FUNCS:
            if self.take() != ("op", "("): self.err(f"'{t[1]}' needs parentheses")
            args = [self.expr()]
            while self.peek() == ("op", ","): self.take(); args.append(self.expr())
            if self.take() != ("op", ")"): self.err("missing ')'")
            if len(args) != FUNCS[t[1]]: self.err(f"{t[1]}() takes {FUNCS[t[1]]} argument(s)")
            return ("call", t[1], args)
        if t[0] == "name":
            if t[1] not in VARS: self.err(f"unknown variable '{t[1]}'")
            return ("var", t[1])
        if t == ("op", "-"): return ("neg", self.factor())
        if t == ("op", "("):
            n = self.expr()
            if self.take() != ("op", ")"): self.err("missing ')'")
            return n
        self.err("expression expected")
    def cond(self):
        a = self.expr(); t = self.take()
        if t is None or t[0] != "op" or t[1] not in (">", "<", ">=", "<=", "==", "!="): self.err("comparison (> < >= <= == !=) expected")
        return ("cmp", t[1], a, self.expr())
    def done(self):
        if self.i < len(self.t): self.err(f"unexpected '{self.t[self.i][1]}'")

def parse_command(text, line):
    """Returns dict instruction."""
    words = text.strip().split(None, 1)
    cmd = words[0].lower(); rest = words[1] if len(words) > 1 else ""
    def ex(s):
        p = P(tokenize(s, line), line); e = p.expr(); p.done(); return e
    def cd(s):
        p = P(tokenize(s, line), line); c = p.cond(); p.done(); return c
    if cmd in ("throttle", "pitch") and re.search(r"\buntil\b", rest, re.I):
        a, c = re.split(r"\buntil\b", rest, maxsplit=1, flags=re.I)
        if not a.strip(): raise ParseError(line, f"'{cmd} ... until' needs a value before 'until'")
        return dict(op="track", target=cmd, arg=ex(a), cond=cd(c), line=line)
    if cmd in ("throttle", "pitch", "warp"):
        if not rest: raise ParseError(line, f"'{cmd}' needs a value")
        return dict(op=cmd, arg=ex(rest), line=line)
    if cmd == "sas":
        m = rest.strip().lower()
        if m not in SAS_MODES: raise ParseError(line, "sas mode must be one of: " + ", ".join(sorted(SAS_MODES)))
        return dict(op="sas", mode=m, line=line)
    if cmd == "stage": return dict(op="stage", line=line)
    if cmd == "end": return dict(op="end", line=line)
    if cmd == "print":
        return dict(op="print", text=rest.strip().strip('"'), line=line)
    if cmd == "wait":
        if rest.lower().startswith("until"):
            return dict(op="wait_until", cond=cd(rest[5:]), line=line)
        if not rest: raise ParseError(line, "'wait' needs seconds or 'until <cond>'")
        return dict(op="wait", arg=ex(rest), line=line)
    if cmd == "if":
        m = re.match(r"(.*?)\bthen\b(.*)", rest, re.I)
        if not m: raise ParseError(line, "'if' needs 'then'")
        inner = parse_command(m.group(2), line)
        if inner["op"] in ("wait_until", "wait", "if"): raise ParseError(line, "'if' can't contain wait/if")
        return dict(op="if", cond=cd(m.group(1)), then=inner, line=line)
    raise ParseError(line, f"unknown command '{cmd}'")

def parse(source):
    """Returns (program, errors[list of (line, msg)])."""
    prog, errs = [], []
    for n, raw in enumerate(source.splitlines(), 1):
        text = raw.split("#", 1)[0].strip()
        if not text: continue
        try: prog.append(parse_command(text, n))
        except ParseError as e: errs.append((e.line, e.msg))
    return prog, errs
