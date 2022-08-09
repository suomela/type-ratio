import collections
import hashlib
import os
import os.path
import re
import subprocess
import statistics
import sys
import jinja2
import markupsafe

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.colors as mcol

infty = float("inf")

DIR = "type-ratio-data"
DIR_IN = os.path.join(DIR, "in")
DIR_OUT = os.path.join(DIR, "out")
DIR_RESULT = "type-ratio-result"
CODE_DIR = os.path.dirname(os.path.abspath(__file__))


def _numrow(l):
    return " ".join([str(x) for x in l]) + "\n"


def list_periods(samplelist):
    x = set()
    for s in samplelist:
        x |= s.periods
    return sorted(x)


def list_colls(samplelist):
    x = set()
    for s in samplelist:
        x |= s.colls
    return sorted(x)


def filter_period(samplelist, period):
    return [s for s in samplelist if period in s.periods]


def filter_coll(samplelist, coll):
    return [s for s in samplelist if coll in s.colls]


def pretty_period(period):
    a, b = period
    return f"{a}–{b-1}"


def lighter(col, w):
    w = w * 0.7 + 0.3
    rgb = mcol.to_rgb(col)
    h, s, v = mcol.rgb_to_hsv(rgb)
    h, s, v = h, w * s + (1 - w) * 0, w * v + (1 - w) * 1
    return mcol.hsv_to_rgb([h, s, v])


class MyPercentFormatter(matplotlib.ticker.ScalarFormatter):
    def __call__(self, x, pos=None):
        f = super().__call__(x, pos)
        return f + '%'


class Metadata:
    pass


class Sample:
    def __init__(self, label, periods, colls):
        self.label = label
        self.periods = set(periods)
        self.colls = set(colls)
        self.tokens = [set(), set()]
        self.tokenlists = [[], []]

    def feed(self, dataset, token):
        self.tokens[dataset].add(token)
        self.tokenlists[dataset].append(token)


class Point:
    def __init__(self, samplelist):
        self.samplelist = samplelist
        self.tokens = [set(), set()]
        self.tokencounts = [collections.Counter(), collections.Counter()]
        self.samplecounts = [collections.Counter(), collections.Counter()]
        for s in samplelist:
            for i in range(2):
                self.tokens[i] |= s.tokens[i]
                self.tokencounts[i].update(s.tokenlists[i])
                for t in s.tokens[i]:
                    self.samplecounts[i][t] += 1
        self.dim = [len(x) for x in self.tokens]
        self.xx = sum(self.dim)
        self.yy = self.dim[0]


class Curve(Point):
    def __init__(self, metadata, period, samplelist):
        super().__init__(samplelist)
        self.metadata = metadata
        self.period = period
        self.pperiod = pretty_period(period)
        self.is_major = metadata.tick_hook(period)

    def calc_write_input(self):
        self.sorted_tokens = [sorted(tt) for tt in self.tokens]
        self.tokenmaps = [{t: i
                           for i, t in enumerate(tt)}
                          for tt in self.sorted_tokens]
        data = []
        for s in self.samplelist:
            row = []
            for di in range(2):
                part = [self.tokenmaps[di][t] for t in s.tokens[di]]
                part.sort()
                row.append(part)
            data.append(row)
        data.sort()
        sdata = ""
        sdata += _numrow([len(data)] + self.dim)
        for row in data:
            sdata += _numrow(row[0] + [-1] + row[1] + [-1])
        sdata = bytes(sdata, encoding="ascii")
        self.digest = hashlib.sha256(sdata).hexdigest()
        os.makedirs(DIR_IN, exist_ok=True)
        filename = os.path.join(DIR_IN, self.digest)
        print(filename)
        with open(filename, "wb") as f:
            f.write(sdata)

    def calc_read_output(self, best):
        filename = os.path.join(DIR_OUT, best[self.digest])
        print(filename)
        self.cum = []
        with open(filename) as f:
            for line in f:
                values = [int(v) for v in line.rstrip().split()]
                first, last = values[:2]
                rest = values[2:]
                assert 0 <= first <= last <= self.yy + 1
                assert len(rest) == last - first
                s = 0
                cum = [0]
                for i in range(first):
                    cum.append(s)
                for v in rest:
                    s += v
                    cum.append(s)
                for i in range(last, self.yy + 1):
                    cum.append(s)
                assert len(cum) == self.yy + 2
                self.cum.append(cum)
        assert len(self.cum) == self.xx + 1

    def get_med_pct(self, xx):
        if xx > self.xx:
            return None
        else:
            return self.get_med(xx) / xx * 100

    def get_mean_pct(self, xx):
        if xx > self.xx:
            return None
        elif self.cum[xx][-1] == 0:
            # FIXME
            return None
        else:
            return self.get_mean(xx) / xx * 100

    def get_up_pct(self, xx, level):
        if xx == 0:
            return 100
        return self.get_up(xx, level) / xx * 100

    def get_low_pct(self, xx, level):
        if xx == 0:
            return 0
        return self.get_low(xx, level) / xx * 100

    def get_med(self, xx):
        a = self.get_up(xx, 0.5)
        b = self.get_low(xx, 0.5)
        return (a + b) / 2

    def get_mean(self, xx):
        row = self.cum[xx]
        tot = row[-1]
        s = 0
        for yy in range(self.yy + 1):
            d = row[yy + 1] - row[yy]
            s += yy * d
        return s / tot

    def get_up(self, xx, level):
        row = self.cum[xx]
        tot = row[-1]
        exp = tot * (1.0 - level)
        yy = self.yy
        while yy > 0 and row[yy] >= exp:
            yy -= 1
        return yy

    def get_low(self, xx, level):
        row = self.cum[xx]
        tot = row[-1]
        exp = tot * level
        yy = 0
        while yy + 1 < len(row) and row[yy + 1] <= exp:
            yy += 1
        return yy


class MultiCurve(Curve):
    def __init__(self, metadata, period, colls, samplelist):
        super().__init__(metadata, period, samplelist)
        self.colls = colls
        self.points = {}
        self.pointlist = []
        for coll in colls:
            sl = filter_coll(samplelist, coll)
            point = Curve(metadata, period, sl)
            point.coll = coll
            self.points[coll] = point
            self.pointlist.append(point)

    def calc_write_input_all(self):
        self.calc_write_input()
        for point in self.pointlist:
            point.calc_write_input()

    def calc_read_output_all(self, best):
        self.calc_read_output(best)
        for point in self.pointlist:
            point.calc_read_output(best)

    def get_min_xx(self):
        return min([p.xx for p in self.pointlist])

    def get_pct(self, coll):
        point = self.points[coll]
        if point.xx == 0:
            return None
        else:
            return point.yy / point.xx * 100

    def get_up_pct_coll(self, coll, level):
        return self.get_up_pct(self.points[coll].xx, level)

    def get_low_pct_coll(self, coll, level):
        return self.get_low_pct(self.points[coll].xx, level)

    def print_point(self, point, f):
        if point.xx == 0:
            return
        frac = point.yy / point.xx
        m = f"  {point.yy:4d}/{point.xx:4d} ≈ {frac*100:5.1f}% {self.metadata.dataset_labels[0]}"

        row = self.cum[point.xx]
        tot = row[-1]
        as_small = row[point.yy + 1] / tot
        as_large = 1 - row[point.yy] / tot
        m += f" : {as_small*100:6.2f}% as small, {as_large*100:6.2f}% as large"

        marks = ""
        x = as_small
        while x <= .1 and len(marks) < 5:
            marks += "-"
            x *= 10
        x = as_large
        while x <= .1 and len(marks) < 5:
            marks += "+"
            x *= 10
        m += f"   {marks:5}"

        m += f"  {point.coll} = {self.metadata.coll_labels[point.coll]}"

        print(m, file=f)

    def print_point_freq(self, point, f, top):
        print(
            f"{self.pperiod}, {point.coll} = {self.metadata.coll_labels[point.coll]}:",
            file=f)
        print(file=f)
        for i in range(2):
            print(f"   {self.metadata.dataset_labels[i]}:", file=f)
            l = sorted(point.tokencounts[i].most_common(),
                       key=lambda x: (-x[1], x[0]))
            if top is not None:
                l = l[:top]
            for w, c in l:
                sc = point.samplecounts[i][w]
                print(f"    {c:8d} tokens {sc:4d} samples:  {w}", file=f)
        print(file=f)

    def print_summary(self, f):
        print(f" {self.pperiod}:", file=f)
        print(file=f)
        for point in self.pointlist:
            self.print_point(point, f)
        print(file=f)

    def print_freq(self, f, top):
        for point in self.pointlist:
            self.print_point_freq(point, f, top)

    def plot(self, dir_result):
        fig = plt.figure(figsize=(7, 5))
        ax = fig.add_axes([0.12, 0.125, 0.85, 0.86])
        ax.set_ylim(self.metadata.yrange)
        ax.set_xlabel(self.metadata.xlabel, labelpad=15)
        ax.set_ylabel(self.metadata.ylabel, labelpad=8)
        ax.yaxis.set_major_formatter(
            matplotlib.ticker.PercentFormatter(decimals=0))

        xxx = list(range(1, self.xx + 1))
        for f in self.metadata.shading_fraction:
            up = [self.get_up_pct(xx, f) for xx in xxx]
            low = [self.get_low_pct(xx, f) for xx in xxx]
            ax.fill_between(xxx,
                            up,
                            low,
                            color="#000000",
                            alpha=0.1,
                            linewidth=0)

        for coll in self.colls:
            point = self.points[coll]
            if point.xx == 0:
                continue
            pct = point.yy / point.xx * 100
            ax.plot(point.xx,
                    pct,
                    color=self.metadata.coll_colors[coll],
                    marker="o")
            f = min(self.metadata.shading_fraction)
            up = self.get_up_pct(point.xx, f)
            low = self.get_low_pct(point.xx, f)
            ax.plot([point.xx, point.xx], [up, low],
                    color=self.metadata.coll_colors[coll],
                    linewidth=2,
                    ls=":")

        basename = f"period-{self.period[0]}-{self.period[1]-1}"
        os.makedirs(dir_result, exist_ok=True)
        if self.metadata.pdf:
            filename = os.path.join(dir_result, f"{basename}.pdf")
            print(filename)
            fig.savefig(filename)
        if self.metadata.png:
            filename = os.path.join(dir_result, f"{basename}.png")
            print(filename)
            fig.savefig(filename, dpi=self.metadata.png)
        plt.close(fig)


class TimeSeries:
    def __init__(self, metadata, colls, samplelist):
        self.metadata = metadata
        self.colls = colls
        self.samplelist = samplelist
        self.curves = {}
        self.curvelist = []
        for period in metadata.periods:
            sl = filter_period(samplelist, period)
            curve = MultiCurve(metadata, period, colls, sl)
            self.curves[period] = curve
            self.curvelist.append(curve)

    def print_summary(self, f):
        print(self.metadata.title, file=f)
        print(file=f)
        for curve in self.curvelist:
            curve.print_summary(f)

    def print_freq(self, f, top):
        print(self.metadata.title, file=f)
        print(file=f)
        for curve in self.curvelist:
            curve.print_freq(f, top)

    def illustrate_freq(self, dir_result):
        self.illustrate_freq_coll(dir_result, None)
        for coll in self.colls:
            self.illustrate_freq_coll(dir_result, coll)

    def illustrate_freq_coll(self, dir_result, coll):
        scale = 1000
        limit_pct = 1
        limit_freq = 2
        minperiods = 2

        col_totals = [collections.Counter(), collections.Counter()]
        token_totals = [collections.Counter(), collections.Counter()]
        token_counts = [collections.Counter(), collections.Counter()]
        overall = [0, 0]
        columns = []
        for curve in self.curvelist:
            col = curve.period
            columns.append({
                'id': col,
                'label': curve.period[0],
                'label2': curve.period[1] - 1
            })
            if coll:
                p = curve.points[coll]
            else:
                p = curve
            for i in range(2):
                for t, count in p.tokencounts[i].items():
                    token_counts[i][(t, col)] += count
                    token_totals[i][t] += count
                    col_totals[i][col] += count
                    overall[i] += count

        col_totals_s = col_totals[0] + col_totals[1]
        token_totals_s = token_totals[0] + token_totals[1]
        token_counts_s = token_counts[0] + token_counts[1]
        overall_s = sum(overall)

        tokens = list(token_totals_s.keys())
        relevant_tokens = collections.Counter()
        tot_pct = collections.Counter()

        for curve in self.curvelist:
            col = curve.period
            s = col_totals_s[col]
            for t in tokens:
                x = token_counts_s[(t, col)]
                if x:
                    tot_pct[t] += x / s
                    if x / s >= limit_pct / 100 and x >= limit_freq:
                        relevant_tokens[t] += 1

        tokens = [t for t in tokens if relevant_tokens[t] >= minperiods]
        tokens.sort()
        tokens.sort(key=lambda x: tot_pct[x], reverse=True)

        heights1 = [{}, {}]
        heights2 = [{}, {}]
        heights3 = [{}, {}]
        for i in range(2):
            for curve in self.curvelist:
                col = curve.period
                s = col_totals_s[col]
                for t in tokens:
                    x = token_counts[i][(t, col)]
                    f1 = max((x - 1) / s, 0)
                    f2 = x / s
                    f3 = (x + 1) / s
                    f1 = round(f1 * scale)
                    f2 = round(f2 * scale)
                    f3 = round(f3 * scale)
                    heights1[i][(t, col)] = f1
                    heights2[i][(t, col)] = f2 - f1
                    heights3[i][(t, col)] = f3 - f2

        title = self.metadata.title
        subtitle = None
        if coll:
            subtitle = self.metadata.coll_labels[coll]

        notes = f'Types that contributed at least {limit_pct}% and had frequency at least {limit_freq} in at least {minperiods} of the time periods.'

        data = {
            'title': title,
            'subtitle': subtitle,
            'notes': notes,
            'datasets': self.metadata.datasets,
            'tokens': tokens,
            'columns': columns,
            'counts': token_counts,
            'heights1': heights1,
            'heights2': heights2,
            'heights3': heights3,
        }

        basename = 'tokens'
        if coll:
            basename += '-' + coll
        filename = os.path.join(dir_result, f"{basename}.html")
        jenv = jinja2.Environment(
            loader=jinja2.FileSystemLoader(CODE_DIR),
            autoescape=True,
        )
        jtempl = jenv.get_template('templates/tokens.html')
        with open(filename, 'w') as f:
            f.write(jtempl.render(data))

    def plot(self, dir_result):
        self.plot_trend_coll(dir_result, True, [])
        for coll in self.colls:
            self.plot_trend_coll(dir_result, True, [coll])
        self.plot_trend_coll(dir_result, False, self.colls)
        for highlight in [None] + self.metadata.periods_highlight:
            self.plot_timeseries(dir_result, highlight)
            for coll in self.colls:
                self.plot_timeseries_coll(dir_result, coll, highlight)
        for curve in self.curvelist:
            curve.plot(dir_result)

    def plot_start(self):
        fig = plt.figure(figsize=(7, 5))
        ax = fig.add_axes([0.13, 0.14, 0.84, 0.84])
        ax.set_ylim(self.metadata.yrange)
        ax.set_xlabel(self.metadata.timeseries_xlabel, labelpad=15)
        ax.set_ylabel(self.metadata.ylabel, labelpad=8)
        years = [p[0] for p in self.metadata.periods]
        major_years = [c.period[0] for c in self.curvelist if c.is_major]
        ax.set_xticks(years, minor=True)
        ax.set_xticks(major_years, minor=False)
        ax.set_xticklabels([c.pperiod for c in self.curvelist if c.is_major],
                           minor=False)
        ax.yaxis.set_major_formatter(MyPercentFormatter())
        for y in major_years:
            ax.axvline(y, color="#000000", linewidth=1, alpha=0.1)
        ax.tick_params(which='major', length=6)
        ax.tick_params(which='minor', length=2)
        return fig, ax, years

    def plot_finish(self, fig, dir_result, basename):
        os.makedirs(dir_result, exist_ok=True)
        if self.metadata.pdf:
            filename = os.path.join(dir_result, f"{basename}.pdf")
            print(filename)
            fig.savefig(filename)
        if self.metadata.png:
            filename = os.path.join(dir_result, f"{basename}.png")
            print(filename)
            fig.savefig(filename, dpi=self.metadata.png)
        plt.close(fig)

    def plot_trend_coll(self, dir_result, show_full, colls):
        only_full = len(colls) == 0

        fig, ax, years = self.plot_start()

        def maxN(l):
            return max([0 if x is None else x for x in l])

        def minN(l):
            return min([infty if x is None else x for x in l])

        xx = self.metadata.trend_step[-1]

        ymax = 0
        ymin = infty

        if show_full:
            col = "#000000" if only_full else "#808080"
            for i in self.metadata.trend_step:
                pct = [c.get_mean_pct(i) for c in self.curvelist]
                ymax = max(ymax, maxN(pct))
                ymin = min(ymin, minN(pct))
                ax.plot(years,
                        pct,
                        color=lighter(col, i / xx),
                        linewidth=2 if only_full else 1,
                        markersize=6 if only_full else 2,
                        marker="o")

        for coll in colls:
            col = self.metadata.coll_colors[coll]
            for i in self.metadata.trend_step:
                pct = [c.points[coll].get_mean_pct(i) for c in self.curvelist]
                ymax = max(ymax, maxN(pct))
                ymin = min(ymin, minN(pct))
                w = 1 - i / xx
                ax.plot(years,
                        pct,
                        color=lighter(col, i / xx),
                        linewidth=2,
                        markersize=6,
                        marker="o")

        if ymin < 0.4 * ymax:
            ymin = 0
        delta = ymax - ymin
        margin = 0.05 * delta
        if 'trend_yrange' in self.metadata.__dict__:
            ax.set_ylim(self.metadata.trend_yrange)
        else:
            ax.set_ylim([ymin - margin, ymax + margin])

        basename = "trend"
        for coll in sorted(colls):
            basename += "-" + coll
        self.plot_finish(fig, dir_result, basename)

    def plot_timeseries(self, dir_result, highlight):
        fig, ax, years = self.plot_start()

        if highlight:
            c = self.curves[highlight]
            ax.axvline(c.period[0],
                       color="#000000",
                       linewidth=2,
                       ls=":",
                       alpha=0.5)

        for coll in self.colls:
            pct = [c.get_pct(coll) for c in self.curvelist]
            ax.plot(years,
                    pct,
                    color=self.metadata.coll_colors[coll],
                    linewidth=2,
                    marker="o")

        basename = f"timeseries"
        if highlight:
            basename += f"-{highlight[0]}-{highlight[1]-1}"

        self.plot_finish(fig, dir_result, basename)

    def plot_timeseries_coll(self, dir_result, coll, highlight):
        fig, ax, years = self.plot_start()

        pct = [c.get_pct(coll) for c in self.curvelist]
        for f in self.metadata.shading_fraction:
            up = [c.get_up_pct_coll(coll, f) for c in self.curvelist]
            low = [c.get_low_pct_coll(coll, f) for c in self.curvelist]
            ax.fill_between(years,
                            up,
                            low,
                            color=self.metadata.coll_colors[coll],
                            alpha=0.15,
                            linewidth=0)
        ax.plot(years,
                pct,
                color=self.metadata.coll_colors[coll],
                linewidth=2,
                marker="o")

        if highlight:
            c = self.curves[highlight]
            f = min(self.metadata.shading_fraction)
            up = c.get_up_pct_coll(coll, f)
            low = c.get_low_pct_coll(coll, f)
            ax.plot([c.period[0], c.period[0]], [up, low],
                    color=self.metadata.coll_colors[coll],
                    linewidth=2,
                    ls=":")

        basename = f"timeseries-{coll}"
        if highlight:
            basename += f"-{highlight[0]}-{highlight[1]-1}"
        self.plot_finish(fig, dir_result, basename)


class Driver:
    def __init__(self, label):
        self.timeseries = []
        self.curves = []
        self.label = label
        self.dir_result = DIR_RESULT + "-" + label

    def add_timeseries(self, ts):
        self.timeseries.append(ts)
        self.curves.extend(ts.curvelist)

    def calc(self, iter):
        print()
        print("*** Calculation")
        print()
        for curve in self.curves:
            curve.calc_write_input_all()
        args = [os.path.join(CODE_DIR, "build/type-ratio"), str(iter)]
        print(" ".join(args))
        subprocess.run(args, check=True)
        print()
        print("*** Read result")
        print()
        self.clean()
        self.find_best()
        for curve in self.curves:
            curve.calc_read_output_all(self.best)
        print()
        print("*** Process result")
        print()
        summaryfile = os.path.join(self.dir_result, "summary.txt")
        with open(summaryfile, "w") as f:
            for ts in self.timeseries:
                ts.print_summary(sys.stdout)
                ts.print_summary(f)
        print()
        for ts in self.timeseries:
            ts.plot(self.dir_result)
        freqfile = os.path.join(self.dir_result, "freq.txt")
        with open(freqfile, "w") as f:
            for ts in self.timeseries:
                ts.print_freq(f, None)
        freqfile = os.path.join(self.dir_result, "freq-5.txt")
        with open(freqfile, "w") as f:
            for ts in self.timeseries:
                ts.print_freq(f, 5)
        for ts in self.timeseries:
            ts.illustrate_freq(self.dir_result)

    def clean(self):
        os.makedirs(self.dir_result, exist_ok=True)
        for fn in os.listdir(self.dir_result):
            os.unlink(os.path.join(self.dir_result, fn))

    def find_best(self):
        by_digest = collections.defaultdict(list)
        for fn in os.listdir(DIR_OUT):
            m = re.fullmatch(r"([0-9a-f]{64})((?:\.[0-9]+)?)", fn)
            assert m is not None, fn
            digest = m.group(1)
            suffix = m.group(2)
            if len(suffix) == 0:
                q = infty
            else:
                q = int(suffix[1:])
            by_digest[digest].append((q, fn))
        self.best = {}
        for digest in by_digest.keys():
            l = sorted(by_digest[digest], reverse=True)
            self.best[digest] = l[0][1]
            for q, fn in l[1:]:
                os.unlink(os.path.join(DIR_OUT, fn))
