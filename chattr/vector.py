import math


class Vector(object):
    __slots__ = 'x', 'y'

    def __init__(self, x=0, y=0):
        self.x = x
        self.y = y

    def __repr__(self):
        return str(self)

    def __str__(self):
        return 'Point(%s, %s)' % (self.x, self.y)

    def __json__(self):
        return list(self)

    def __add__(self, vec):
        if not isinstance(vec, Vector):
            raise TypeError('Cannot add Vector and %s' % vec)

        return Vector(self.x + vec.x, self.y + vec.y)

    def __iadd__(self, vec):
        if not isinstance(vec, Vector):
            raise TypeError('Cannot add %s to Vector' % vec)

        self.x += vec.x
        self.y += vec.y
        return self

    def __sub__(self, vec):
        if not isinstance(vec, Vector):
            raise TypeError('Cannot subtract Vector and %s' % vec)

        return Vector(self.x - vec.x, self.y - vec.y)

    def __isub__(self, vec):
        if not isinstance(vec, Vector):
            raise TypeError('Cannot subtract %s from Vector' % vec)

        self.x -= vec.x
        self.y -= vec.y
        return self

    def __mul__(self, v):
        return Vector(self.x * v, self.y * v)

    def __imul__(self, v):
        self.x *= v
        self.y *= v
        return self

    def __div__(self, v):
        return Vector(self.x / v, self.y / v)

    def __idiv__(self, v):
        self.x /= v
        self.y /= v
        return self

    def __len__(self):
        return 2

    def __getitem__(self, index):
        return (self.x, self.y)[index]

    def __setitem__(self, index, value):
        temp = [self.x, self.y]
        temp[index] = value
        self.x, self.y = temp

    def __iter__(self):
        yield self.x
        yield self.y

    def __reversed__(self):
        yield self.y
        yield self.x

    def __contains__(self, obj):
        return obj in (self.x, self.y)

    def __pos__(self):
        return Vector(+self.x, +self.y)

    def __neg__(self):
        return Vector(-self.x, -self.y)

    copy = __pos__

    def zero(self):
        self.x = self.y = 0

    @property
    def magnitude(self):
        return math.hypot(self.x, self.y)

    def normalize(self):
        self /= self.magnitude
        return self

    def unit(self):
        return self.copy().normalize()

    def dot(self, vec):
        return self.x * vec.x + self.y * vec.y

    def cross(self, vec):
        return self.x * vec.y - self.y * vec.x

    def distance(self, vec):
        tmp = vec.copy()
        tmp -= self
        return tmp.magnitude

Point = Vector
