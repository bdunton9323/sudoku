
class Tester(object):
    def __init__(self):
        self.values = [1, 2, 3, 4, 5]

    @property
    def values(self):
        return self._values

    @values.setter
    def values(self, v):
        self._values = v


t = Tester()
print(t.values)
print(set(t.values))