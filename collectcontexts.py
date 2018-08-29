#!/usr/bin/env python3
from argparse import ArgumentParser
import os
import pickle

from tf.fabric import Fabric

from hebrewreader import DATADIR, FEATURES, load_data
from minitf import gather_context

VERSE_NODES = dict()

def gather_chapter(api, book, chap):
    global VERSE_NODES
    nodes = set()
    node = api.T.nodeFromSection((book, chap, 1))
    if node is None:
        return None
    verse = 1
    VERSE_NODES[book][chap] = dict()
    while api.T.sectionFromNode(node)[0:2] == (book,chap):
        verse = api.T.sectionFromNode(node)[2]
        VERSE_NODES[book][chap][verse] = node
        nodes.add(node)
        words = api.L.d(node, 'word')
        nodes.update(set(words))
        for word in words:
            nodes.update(set(api.L.u(word, 'lex')))
        next_verse = api.L.n(node, 'verse')
        if next_verse == ():
            break
        node = next_verse[0]
    return nodes

def gather_book(api, book):
    global VERSE_NODES
    result = dict()
    chap = 1
    VERSE_NODES[book] = dict()
    while True:
        nodes = gather_chapter(api, book, chap)
        if nodes is None:
            return result
        result[chap] = nodes
        chap += 1

def dump_book(api, book):
    nodesets = gather_book(api, book)
    for chap, nodes in nodesets.items():
        context = gather_context(
                api,
                {'features': FEATURES, 'locality': 'udnp'},
                (nodes,))
        fname = book + '_' + str(chap) + '.pkl'
        with open(os.path.join(DATADIR, fname), 'wb') as f:
            pickle.dump(context, f)

def gather(locations, modules):
    TF = Fabric(locations=locations, modules=modules, silent=True)
    api = TF.load(FEATURES, silent=True)

    for node in api.F.otype.s('book'):
        book = api.T.sectionFromNode(node)[0]
        print(book)
        dump_book(api, book)

    with open(os.path.join(DATADIR, 'verse_nodes.pkl'), 'wb') as f:
        pickle.dump(VERSE_NODES, f)

def main():
    parser = ArgumentParser(description='Gather the TF contexts to reduce memory usage in the HTTP server')

    p_data = parser.add_argument_group('Data source options')
    p_data.add_argument('--bhsa', '-b', nargs=1, required=True,
            help='Location of the BHSA data')
    p_data.add_argument('--module', '-m', nargs=1, required=True,
            help='Text-fabric module to load')

    args = parser.parse_args()

    gather(args.bhsa, args.module)

if __name__ == '__main__':
    main()
