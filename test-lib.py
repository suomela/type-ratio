#!/usr/bin/env python3

import random
import type_ratio

p1, p2, p3, p4 = (1500, 1600), (1600, 1700), (1700, 1800), (1800, 1900)

def get_metadata():
    metadata = type_ratio.Metadata()
    metadata.datasets = ['suffix1', 'suffix2']
    metadata.dataset_labels = ['Suffix 1', 'Suffix 2']
    metadata.title = 'Example title'
    metadata.xlabel = 'Suffix 1 and 2 types'
    metadata.ylabel = 'Proportion of suffix 1 types'
    metadata.timeseries_xlabel = 'Time period'
    metadata.coll_labels = {'X': 'Collection X', 'Y': 'Collection Y'}
    metadata.coll_colors = {'X': '#f26924', 'Y': '#0088cc'}
    metadata.periods = [p1, p2, p3, p4]
    metadata.periods_highlight = [p2]
    metadata.tick_hook = lambda x: x[0] % 100 == 0
    metadata.shading_fraction = [0.1, 0.025]  # 80%, 95%
    metadata.yrange = [0, 100]
    metadata.trend_yrange = [0, 100]
    metadata.trend_step = [100]
    metadata.pdf = True
    metadata.png = None
    # metadata.png=400
    return metadata

samplecounter = 1

def sample(periods, colls, tokens1, tokens2):
    global samplecounter
    label = f'sample{samplecounter}'
    samplecounter += 1
    s = type_ratio.Sample(label, periods, colls)
    for t in tokens1:
        s.feed(0, t)
    for t in tokens2:
        s.feed(1, t)
    return s

def random_subset(x, p):
    y = []
    for c in x:
        if random.random() < p:
            y.append(c)
    return y

def get_test_data1():
    return [
        sample([p1], ['X'], ['a'], ['A']),
    ]

def get_test_data2(pp):
    random.seed(0)
    tokens1a = [ f'ta{i}' for i in range(200) ]
    tokens1b = [ f'tb{i}' for i in range(200) ]
    tokens2a = [ f'TA{i}' for i in range(200) ]
    tokens2b = [ f'TB{i}' for i in range(200) ]
    samplelist = []
    for p in [p1, p2, p3, p4]:
        for i in range(100):
            for c in ['X', 'Y']:
                tokens1 = random_subset(tokens1a, pp[(c,1)][0]) + random_subset(tokens1b, pp[(c,1)][1])
                tokens2 = random_subset(tokens2a, pp[(c,2)][0]) + random_subset(tokens2b, pp[(c,2)][1])
                samplelist.append(sample([p], [c], tokens1, tokens2))
    return samplelist

def run(name, samplelist):
    driver = type_ratio.Driver(name)
    colls = type_ratio.list_colls(samplelist)
    ts = type_ratio.TimeSeries(get_metadata(), colls, samplelist)
    driver.add_timeseries(ts)
    driver.calc(10000)

def main():
    run('test1', get_test_data1())
    run('test2a', get_test_data2({
        # flat
        ('X', 1): [0.1, 0.01],
        ('X', 2): [0.1, 0.01],
        ('Y', 1): [0.1, 0.01],
        ('Y', 2): [0.1, 0.01],
    }))
    run('test2b', get_test_data2({
        # 1–2 difference but no X–Y difference
        ('X', 1): [0.1, 0.0001],
        ('X', 2): [0.1, 0.01],
        ('Y', 1): [0.1, 0.0001],
        ('Y', 2): [0.1, 0.01],
    }))
    run('test2c', get_test_data2({
        # some X–Y difference
        ('X', 1): [0.1, 0.0001],
        ('X', 2): [0.1, 0.01],
        ('Y', 1): [0.1, 0.01],
        ('Y', 2): [0.1, 0.01],
    }))

main()
