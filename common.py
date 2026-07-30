import os
import pickle

import minitf

DATADIR = 'data'

FEATURES = 'g_word_utf8 gloss lex_utf8 otype trailer_utf8 voc_lex_utf8'

verse_nodes = None
def load_verse_nodes():
    global verse_nodes

    if verse_nodes is None:
        with open(os.path.join(DATADIR, 'verse_nodes.pkl'), 'rb') as f:
            verse_nodes = pickle.load(f)

    return verse_nodes

def verses_in_passage(passage):
    verse_nodes = load_verse_nodes()

    for chap in range(passage['startchap'], passage['endchap']+1):
        start = passage['startverse'] if chap == passage['startchap'] else 1
        if chap == passage['endchap']:
            end = passage['endverse']
        else:
            end = len(verse_nodes[passage['book']][chap])

        for verse in range(start, end+1):
            yield (passage['book'], chap, verse)

def load_data(passage):
    seen = set()
    context = dict()
    for book, chap, _ in verses_in_passage(passage):
        if (book,chap) in seen:
            continue
        seen.add((book, chap))
        fname = book + '_' + str(chap) + '.pkl'
        with open(os.path.join(DATADIR, fname), 'rb') as f:
            add_context = pickle.load(f)
            for key, val in add_context.items():
                if key not in context:
                    context[key] = val
                elif key == 'nodes':
                    context[key] += ',' + val
                elif key == 'locality' or key == 'features':
                    for subkey, subval in val.items():
                        context[key][subkey].update(subval)
                else:
                    context[key].update(val)
    api = minitf.MiniApi(**context)
    return api
