import math

WARPS = [1, 2, 4, 10, 50, 100, 1000, 10000, 100000]

def evaluate(node, tel):
    k = node[0]
    if k == "num": return node[1]
    if k == "var": return getattr(tel, node[1])
    if k == "neg": return -evaluate(node[1], tel)
    if k == "+": return evaluate(node[1], tel) + evaluate(node[2], tel)
    if k == "-": return evaluate(node[1], tel) - evaluate(node[2], tel)
    if k == "*": return evaluate(node[1], tel) * evaluate(node[2], tel)
    if k == "/":
        d = evaluate(node[2], tel)
        return evaluate(node[1], tel) / d if d else math.inf
    if k == "call":
        a = [evaluate(x, tel) for x in node[2]]; f = node[1]
        if f == "sqrt": return math.sqrt(max(a[0], 0.0))
        if f == "abs": return abs(a[0])
        if f == "min": return min(a)
        if f == "max": return max(a)
    raise ValueError(k)

def cond_true(c, tel):
    _, op, a, b = c
    x, y = evaluate(a, tel), evaluate(b, tel)
    return {">": x > y, "<": x < y, ">=": x >= y, "<=": x <= y, "==": x == y, "!=": x != y}[op]

class Executor:
    def __init__(self, program):
        self.prog = program; self.pc = 0; self.finished = not program
        self.wait_until = None; self.wait_cond = None
        self.enabled = True

    @property
    def current_line(self):
        return self.prog[self.pc]["line"] if self.pc < len(self.prog) else None

    def tick(self, sim):
        if not self.enabled or self.finished: return
        tel = None
        guard = 0
        while self.pc < len(self.prog) and guard < 50:
            guard += 1
            ins = self.prog[self.pc]
            op = ins["op"]
            if op == "wait_until":
                tel = sim.telemetry()
                if not cond_true(ins["cond"], tel): return
                self.pc += 1; continue
            if op == "track":
                tel = sim.telemetry()
                if cond_true(ins["cond"], tel): self.pc += 1; continue
                v = evaluate(ins["arg"], tel)
                if ins["target"] == "throttle": sim.set_throttle(v)
                else: sim.set_sas("pitch", v)
                return
            if op == "wait":
                if self.wait_until is None:
                    self.wait_until = sim.t + evaluate(ins["arg"], sim.telemetry())
                if sim.t < self.wait_until: return
                self.wait_until = None; self.pc += 1; continue
            self._run(ins, sim)
            self.pc += 1
        if self.pc >= len(self.prog):
            self.finished = True; sim.note("Script finished")

    def _run(self, ins, sim):
        op = ins["op"]
        if op == "if":
            if cond_true(ins["cond"], sim.telemetry()): self._run(ins["then"], sim)
            return
        if op == "throttle": sim.set_throttle(evaluate(ins["arg"], sim.telemetry()))
        elif op == "pitch": sim.set_sas("pitch", evaluate(ins["arg"], sim.telemetry()))
        elif op == "sas": sim.set_sas(ins["mode"])
        elif op == "stage": sim.stage()
        elif op == "print": sim.note("> " + ins["text"])
        elif op == "warp":
            w = evaluate(ins["arg"], sim.telemetry())
            sim.requested_warp = min(WARPS, key=lambda x: abs(x - w))
        elif op == "end": self.finished = True; self.pc = len(self.prog)
