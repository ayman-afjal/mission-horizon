class FuelPool:
    def __init__(self, capacity=0.0):
        self.capacity = capacity; self.amount = capacity
    def draw(self, kg):
        used = min(kg, self.amount); self.amount -= used; return used
    @property
    def fraction(self): return self.amount / self.capacity if self.capacity > 0 else 0.0
