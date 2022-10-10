#!/usr/bin/env python3
from argparse import ArgumentParser
import os
import pickle

from tf.fabric import Fabric

from hebrewreader import DATADIR, FEATURES, SYR_FEATURES, load_data
from minitf import gather_context

VERSE_NODES = dict()

def gather_chapter(api, book, chap, lang):
    global VERSE_NODES
    nodes = set()
    node = api.T.nodeFromSection((book, chap, 1))
    if node is None:
        return None
    verse = 1
    VERSE_NODES[lang][book][chap] = dict()
    while api.T.sectionFromNode(node)[0:2] == (book,chap):
        verse = api.T.sectionFromNode(node)[2]
        VERSE_NODES[lang][book][chap][verse] = node
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

def gather_book(api, book, lang):
    global VERSE_NODES
    result = dict()
    chap = 1
    VERSE_NODES[lang][book] = dict()
    while True:
        nodes = gather_chapter(api, book, chap, lang)
        if nodes is None:
            return result
        result[chap] = nodes
        chap += 1

def dump_book(api, book, lang, use_features):
    nodesets = gather_book(api, book, lang)
    for chap, nodes in nodesets.items():
        context = gather_context(
                api,
                {'features': use_features, 'locality': 'udnp'},
                (nodes,))
        fname = lang + '_' + book + '_' + str(chap) + '.pkl'
        with open(os.path.join(DATADIR, fname), 'wb') as f:
            pickle.dump(context, f)

def gather(locations, modules, lang):
    global VERSE_NODES
    TF = Fabric(locations=locations, modules=modules, silent=True)
    if lang[0] == 'syriac':
        use_features = SYR_FEATURES
    else:
        use_features = FEATURES
    api = TF.load(use_features, silent=True)

    VERSE_NODES[lang[0]] = {}

    for node in api.F.otype.s('book'):
        book = api.T.sectionFromNode(node)[0]
        dump_book(api, book, lang[0], use_features)

    if lang[0] == 'hebrew':
        with open(os.path.join(DATADIR, 'verse_nodes.pkl'), 'wb') as f:
            pickle.dump(VERSE_NODES, f)
    else:
        with open(os.path.join(DATADIR, 'verse_nodes.pkl'), 'rb') as f:
            HEB_VERSE_NODES = pickle.load(f)
            FIN_VERSE_NODES = {
                "hebrew": HEB_VERSE_NODES['hebrew'],
                "syriac": VERSE_NODES['syriac']
            }

            with open(os.path.join(DATADIR, 'verse_nodes.pkl'), 'wb') as f:
                pickle.dump(FIN_VERSE_NODES, f)

def main():
    parser = ArgumentParser(description='Gather the TF contexts to reduce memory usage in the HTTP server')

    p_data = parser.add_argument_group('Data source options')
    p_data.add_argument('--bhsa', '-b', nargs=1, required=True,
            help='Location of the BHSA data')
    p_data.add_argument('--module', '-m', nargs=1, required=True,
            help='Text-fabric module to load')
    p_data.add_argument('--lang', '-l', nargs=1, required=True,
            help='Which language data to load')

    args = parser.parse_args()
    gather(args.bhsa, args.module, args.lang)

if __name__ == '__main__':
    main()
