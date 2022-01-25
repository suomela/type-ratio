#!/usr/bin/env python3

import itertools
import math
import random
import string
import subprocess
import sys
from pathlib import Path

DIR = Path('type-ratio-data')
DIR_IN = DIR / 'in'
DIR_OUT = DIR / 'out'
TOOL = Path('build') / 'type-ratio'


def pretty_in(x):
    if isinstance(x, str):
        return x
    elif isinstance(x, list):
        return ' '.join(map(str, x))


def pretty_out(x):
    return ' '.join(map(str, x))


class Test:
    def __init__(self, data):
        self.data = data
        self.symmap = [None, None]
        self.rsymmap = [None, None]
        self.dim = [None, None]
        self.symbols = [None, None]
        for i in range(2):
            self.symbols[i] = set()
            for row in data:
                self.symbols[i] |= set(row[i])
            symbols = sorted(self.symbols[i])
            self.symmap[i] = {x: i for i, x in enumerate(symbols)}
            self.rsymmap[i] = {i: x for i, x in enumerate(symbols)}
            self.dim[i] = len(symbols)
        assert len(self.symbols[0] & self.symbols[1]) == 0
        self.yy = self.dim[0]
        self.xx = sum(self.dim)

    def dump(self, f):
        print(f'{len(self.data)} {self.dim[0]} {self.dim[1]}', file=f)
        for row in self.data:
            for i in range(2):
                enc = [self.symmap[i][x] for x in row[i]]
                enc = ' '.join(map(str, enc))
                print(f'{enc} -1', file=f)

    def exact(self):
        return math.factorial(len(self.data))

    def load(self, f):
        self.result = []
        for line in f:
            values = [int(v) for v in line.rstrip().split()]
            first, last = values[:2]
            rest = values[2:]
            assert 0 <= first <= last <= self.yy + 1
            assert len(rest) == last - first
            row = []
            for i in range(first):
                row.append(0)
            for v in rest:
                row.append(v)
            for i in range(last, self.yy + 1):
                row.append(0)
            assert len(row) == self.yy + 1
            self.result.append(row)
        assert len(self.result) == self.xx + 1

    def verify_exact(self):
        self.expected = [[0 for y in range(self.yy + 1)]
                         for x in range(self.xx + 1)]
        for case in itertools.permutations(self.data):
            seen_x = set()
            seen_y = set()
            for row in case:
                seen_x |= set(row[0] + row[1])
                seen_y |= set(row[0])
                x = len(seen_x)
                y = len(seen_y)
                self.expected[x][y] += 1
        if self.result != self.expected:
            print('Got:')
            for row in self.result:
                print(f' {row}')
            print('Expected:')
            for row in self.expected:
                print(f' {row}')
            assert False

    def verify_approx(self, sloppiness):
        random.seed(0)
        self.expected = [[0 for y in range(self.yy + 1)]
                         for x in range(self.xx + 1)]
        case = list(self.data)
        for iter in range(1000):
            random.shuffle(case)
            seen_x = set()
            seen_y = set()
            for row in case:
                seen_x |= set(row[0] + row[1])
                seen_y |= set(row[0])
                x = len(seen_x)
                y = len(seen_y)
                self.expected[x][y] += 1
        if not self.approx_match(sloppiness):
            print('Got:')
            for row in self.result:
                print(f' {row}')
            print('Expected:')
            for row in self.expected:
                print(f' {row}')
            assert False

    def approx_match(self, sloppiness):
        bad = 0
        for x in range(self.xx + 1):
            if self.approx_match_row(self.expected[x],
                                     self.result[x]) > sloppiness:
                bad += 1
        bad /= (self.xx + 1)
        if bad > 0.5 * sloppiness:
            print(f'  · pretty bad: {bad}')
        return bad < sloppiness

    def approx_match_row(self, r1, r2):
        r1 = self.normalize_row(r1)
        r2 = self.normalize_row(r2)
        diff = 0
        for y in range(self.yy + 1):
            d = abs(r1[y] - r2[y])
            diff = max(d, diff)
        return diff

    def normalize_row(self, row):
        assert len(row) == self.yy + 1
        s = sum(row)
        if s == 0:
            return row
        else:
            return [x / s for x in row]

    def show(self):
        print('  · input:')
        for a, b in self.data:
            print(f'      {pretty_in(a)}, {pretty_in(b)}')
        print('  · result:')
        for row in self.result:
            print(f'      {pretty_out(row)}')


class Tests:
    def __init__(self, verbose=False):
        self.tests = []
        self.verbose = verbose

    def add(self, data):
        self.tests.append(Test(data))

    def run_exact(self):
        self.run(True)

    def run_approx(self, iterlist):
        self.run(False, iterlist)

    def run(self, run_exact, iterlist=None):
        self.setup()
        if run_exact:
            print('Exact test:')
            assert iterlist is None
            iter = 0
        else:
            print('Approximate test:')
            assert iterlist is not None
        for i, test in enumerate(self.tests):
            fn = DIR_IN / f'{i}'
            print(f'· create {fn}')
            with open(fn, 'w') as f:
                test.dump(f)
            if run_exact:
                iter = max(iter, test.exact())
        if run_exact:
            iterlist = [iter]
        for iter in iterlist:
            print(f'· run {TOOL} {iter}')
            subprocess.run([TOOL, str(iter)], check=True)
            for i, test in enumerate(self.tests):
                fn = DIR_OUT / f'{i}'
                if fn.exists():
                    got_exact = True
                else:
                    got_exact = False
                    fn = DIR_OUT / f'{i}.{iter}'
                print(f'· read {fn}')
                with open(fn) as f:
                    test.load(f)
                if self.verbose:
                    test.show()
                if run_exact:
                    assert got_exact
                test.got_exact = got_exact
        for i, test in enumerate(self.tests):
            if test.got_exact:
                print(f'· verify {i} (exact)')
                test.verify_exact()
                test.verify_approx(0.1)
            elif len(test.data) < 500:
                print(f'· verify {i} (approximate)')
                test.verify_approx(0.25)
        print()
        self.tests = []

    def setup(self):
        for d in [DIR_IN, DIR_OUT]:
            d.mkdir(parents=True, exist_ok=True)
            for f in d.glob('*'):
                f.unlink()


def random_subset(x, p):
    y = []
    for c in x:
        if random.random() < p:
            y.append(c)
    if isinstance(x, str):
        return ''.join(y)
    else:
        return y


def pick_symbols(l, x):
    if x < len(l):
        return l[:x]
    else:
        return [f'{l[0]}{i}' for i in range(x)]


def gen_random(a, b, n):
    random.seed(0)
    asym = pick_symbols(string.ascii_lowercase, a)
    bsym = pick_symbols(string.ascii_uppercase, b)
    data = []
    for i in range(n):
        aa = random_subset(asym, 0.5)
        bb = random_subset(bsym, 0.5)
        data.append([aa, bb])
    return data


def main():
    verbose = 'verbose' in sys.argv[1:]
    t = Tests(verbose)
    t.run_exact()
    t.add([('a', 'A')])
    t.run_exact()
    t.add([('a', 'A')])
    t.add([('abc', 'ABCDEF')])
    t.add([('a', ''), ('', 'A')])
    t.add([('a', 'A'), ('b', 'B'), ('c', 'C'), ('d', 'D')])
    t.run_exact()
    for n in range(8):
        t.add(gen_random(10, 10, n))
        t.add(gen_random(25, 25, n))
        t.add(gen_random(100, 100, n))
    t.run_exact()
    for n in range(8):
        t.add(gen_random(10, 10, n))
        t.add(gen_random(25, 25, n))
        t.add(gen_random(100, 100, n))
    t.run_approx([100])
    for n in range(100, 1000, 100):
        t.add(gen_random(10, 10, n))
        t.add(gen_random(100, 100, n))
    t.run_approx([1000])
    for n in range(1000, 10000, 1000):
        t.add(gen_random(10, 10, n))
        t.add(gen_random(100, 100, n))
    t.run_approx([1000, 2000])


main()
