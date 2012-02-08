from mpl_toolkits.mplot3d import axes3d
import matplotlib.pyplot as plt
import numpy as np
import random
import json
import sys

SIZE = 100
DIM = [SIZE, SIZE]
ITERATIONS = 200
MIN_RADIUS = .1
MAX_RADIUS = .5

# FIXME sprinkle trees etc
# FIXME desert/swamp/locality

TILES = [
    {
        'name': 'deep-water',
        'x': 0,
        'y': 2,
        'w': 32,
        'h': 32,
        'flags': ''
    },
    {
        'name': 'shallow-water',
        'x': 0,
        'y': 12,
        'w': 32,
        'h': 32,
        'flags': ''
    },
    {
        'name': 'sand',
        'x': 3,
        'y': 1,
        'w': 32,
        'h': 32,
        'flags': ''
    },
    {
        'name': 'grass',
        'x': 0,
        'y': 1,
        'w': 32,
        'h': 32,
        'flags': ''
    },
    {
        'name': 'swamp',
        'x': 6,
        'y': 2,
        'w': 32,
        'h': 32,
        'flags': ''
    },
    {
        'name': 'forest',
        'x': 0,
        'y': 6,
        'w': 32,
        'h': 32,
        'flags': ''
    },
    {
        'name': 'everglades',
        'x': 6,
        'y': 6,
        'w': 32,
        'h': 32,
        'flags': ''
    },
    {
        'name': 'hills',
        'x': 3,
        'y': 10,
        'w': 32,
        'h': 32,
        'flags': ''
    },
    {
        'name': 'mountains',
        'x': 0,
        'y': 13,
        'w': 32,
        'h': 32,
        'flags': ''
    },
    {
        'name': 'volcanos',
        'x': 3,
        'y': 13,
        'w': 32,
        'h': 32,
        'flags': ''
    }
]


def generate():
    x, y, z = np.zeros(DIM), np.zeros(DIM), np.zeros(DIM)

    # initialize the arrays
    for j in range(SIZE):
        for k in range(SIZE):
            x[j][k] = -1 + (2 * float(k) / float(SIZE))
            y[k][j] = -1 + (2 * float(k) / float(SIZE))

    for i in range(ITERATIONS):
        print >>sys.stderr, '%.02f' % (float(i) / float(ITERATIONS) * 100)

        cx = random.randint(0, SIZE - 1)
        cy = random.randint(0, SIZE - 1)

        hx, hy = x[cy][cx], y[cy][cx]
        hr = random.uniform(MIN_RADIUS, MAX_RADIUS)

        # FIXME can limit to 2R box around center
        for j in range(SIZE):
            for k in range(SIZE):
                px = x[j][k]
                py = y[j][k]
                z[j][k] += max(hr ** 2 - ((px - hx) ** 2 + (py - hy) ** 2), 0)

    zmin = z.min()
    zmax = z.max()
    z -= zmin
    z /= (zmax - zmin)

    z = np.square(z)

    return x, y, z


def render(data):
    x, y, z = data

    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')
    ax.plot_wireframe(x, y, z, rstride=10, cstride=10)

    plt.show()


def dump(data):
    x, y, z = data

    out = []
    for i in range(SIZE):
        out.append([int(round(10 * x)) for x in z[i]])

    print json.dumps({'tiles': TILES,
                      'data': out,
                      'tile_map': 'terrain-tiles'})


def main():
    data = generate()
    dump(data)
    render(data)

if __name__ == '__main__':
    main()
