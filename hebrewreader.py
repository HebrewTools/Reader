#!/usr/bin/env python3
from argparse import ArgumentParser, FileType, RawTextHelpFormatter
import os
import pickle
import re
from shutil import copyfile
import subprocess
import sys
import tempfile
import textwrap

from tf.fabric import Fabric

import minitf

DATADIR = 'data'

PASSAGE_RGX = (
    r'^(?P<book>(?:\d )?[a-zA-Z ]+) '
    r'(?P<startchap>\d+)(?::(?P<startverse>\d+))?'
    r'(?:-(?P<endref>(?P<endchap>\d+)(?::(?P<endverse>\d+))?|(?:book)?end))?$'
)

FEATURES = 'g_word_utf8 gloss lex_utf8 otype trailer_utf8 voc_lex_utf8'

VERSE_NODES = dict()

def load_verse_nodes():
    global VERSE_NODES

    with open(os.path.join(DATADIR, 'verse_nodes.pkl'), 'rb') as f:
        VERSE_NODES = pickle.load(f)

def parse_passage(passage):
    match = re.match(PASSAGE_RGX, passage)
    if match is None:
        match = {'book': passage, 'startchap': 1, 'startverse': 1,
                'endchap': None, 'endverse': None, 'endref': 'bookend'}
    else:
        match = match.groupdict()

    match['book'] = match['book'].replace(' ', '_')
    match['startchap'] = int(match['startchap'])
    if match['startverse'] is not None:
        match['startverse'] = int(match['startverse'])
    if match['endchap'] is not None:
        match['endchap'] = int(match['endchap'])
    if match['endverse'] is not None:
        match['endverse'] = int(match['endverse'])

    try:
        if match['endchap'] is None:
            if match['startverse'] is None and match['endref'] is None:
                match['endref'] = 'end'
            else:
                match['endchap'] = match['startchap']
                match['endverse'] = match['startverse']
        elif match['endverse'] is None:
            match['endverse'] = len(VERSE_NODES[match['book']][match['endchap']])

        if match['startverse'] is None:
            match['startverse'] = 1

        if match['endref'] == 'end':
            match['endchap'] = match['startchap']
            match['endverse'] = len(VERSE_NODES[match['book']][match['endchap']])
        elif match['endref'] == 'bookend':
            match['endchap'] = len(VERSE_NODES[match['book']])
            match['endverse'] = len(VERSE_NODES[match['book']][match['endchap']])
    except:
        raise ValueError('Could not find reference "{}"'.format(passage))

    match.pop('endref')
    return match

def verses_in_passage(passage):
    for chap in range(passage['startchap'], passage['endchap']+1):
        start = passage['startverse'] if chap == passage['startchap'] else 1
        if chap == passage['endchap']:
            end = passage['endverse']
        else:
            end = len(VERSE_NODES[passage['book']][chap])

        for verse in range(start, end+1):
            yield (passage['book'], chap, verse)

def fix_trailer(trailer, templates):
    return trailer\
            .replace('\n', '')\
            .replace('\u05e1', templates['setuma'])\
            .replace('\u05e4', templates['petucha'])

def fix_gloss(gloss, templates):
    if gloss == 'i':
        return 'I'
    return re.sub(r'<(.*)>', templates['meta_gloss'], gloss)

def get_passage_and_words(passage, api, templates, separate_chapters=True, verse_nos=True):
    text = []
    words = set()

    last_chapter = None
    for verse in verses_in_passage(passage):
        if verse[1] != last_chapter:
            last_chapter = verse[1]
            if separate_chapters:
                text.append('\n')
        node = VERSE_NODES[verse[0]][verse[1]][verse[2]]
        wordnodes = api.L.d(node, otype='word')
        thistext = ''
        if verse_nos:
            if verse[2] == 1:
                thistext += templates['chapno'] % verse[1]
            thistext += templates['verseno'] % verse[2] + ' '
        thiswords = []
        for word in wordnodes:
            thiswords.append(
                    api.F.g_word_utf8.v(word) +
                    fix_trailer(api.F.trailer_utf8.v(word), templates))
            lex = api.L.u(word, otype='lex')[0]
            words.add((api.F.lex_utf8.v(word), api.F.voc_lex_utf8.v(lex), fix_gloss(api.F.gloss.v(lex), templates)))
        thistext += ''.join(thiswords)
        text.append(thistext)

    return text, sorted(words)

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

def generate_txt(passages, include_voca, combine_voca, txt):
    voca = set()

    templates = {
            'chapno': '%d:', 'verseno': '%d',
            'setuma': 'ס', 'petucha': 'פ',
            'meta_gloss': r'<\1>',
            }

    first = True
    for passage_text in passages:
        passage = parse_passage(passage_text)

        if not first:
            txt.write('\n\n')
        first = False

        try:
            api = load_data(passage)
            text, words = get_passage_and_words(passage, api, templates)
        except:
            raise ValueError('Could not find reference "{}"'.format(passage_text))

        passage_pretty = '{} {}:{} - {}:{}'.format(
            passage['book'].replace('_', ' '),
            passage['startchap'], passage['startverse'],
            passage['endchap'], passage['endverse'])
        txt.write(passage_pretty + '\n'.join(text))

        if not include_voca:
            continue

        if combine_voca:
            voca.update(words)
        else:
            txt.write('\n\n' + '\n'.join('%s: %s' % (lex,gloss) for _, lex, gloss in words))

    if include_voca and combine_voca:
        txt.write('\n\n' + '\n'.join('%s: %s' % (lex,gloss) for _, lex, gloss in sorted(voca)))

    txt.close()

    return txt.name

def generate_tex(passages, include_voca, combine_voca, clearpage_before_voca,
        large_text, larger_text, tex, templates):
    tex.write(templates['pre'])

    if large_text:
        tex.write('\\largetexttrue\n')
    if larger_text:
        tex.write('\\largertexttrue\n')

    voca = set()

    text_templates = {
            'chapno': r'\rdrchap{%d}', 'verseno': r'\rdrverse{%d}',
            'setuma': r'\setuma{}', 'petucha': r'\petucha{}',
            'meta_gloss': r'\\textit{\1}',
            }

    for passage_text in passages:
        passage = parse_passage(passage_text)

        passage_pretty = '{} {}:{} - {}:{}'.format(
            passage['book'].replace('_', ' '),
            passage['startchap'], passage['startverse'],
            passage['endchap'], passage['endverse'])
        tex.write(r'\def\thepassage{%s}' % passage_pretty)

        try:
            api = load_data(passage)
            text, words = get_passage_and_words(passage, api, text_templates)
        except:
            raise ValueError('Could not find reference "{}"'.format(passage_text))

        tex.write('\n\n' + templates['pretext'])
        tex.write('\n'.join(text))
        tex.write('\n' + templates['posttext'])

        if not include_voca:
            continue

        if combine_voca:
            voca.update(words)
        else:
            if clearpage_before_voca:
                tex.write('\n\n\\clearpage')
            tex.write('\n\n' + templates['prevoca'])
            tex.write('\\\\\n'.join(r'{\hebrewfont\vocafontsize\RL{%s}} \begin{english}%s\end{english}' % (lex,gloss) for _, lex, gloss in words))
            tex.write('\n' + templates['postvoca'])

    if include_voca and combine_voca:
        if clearpage_before_voca:
            tex.write('\n\n\\clearpage')
        tex.write('\n\n' + templates['prevoca'])
        tex.write('\\\\\n'.join(r'{\hebrewfont\RL{%s}} \begin{english}%s\end{english}' % (lex,gloss) for _, lex, gloss in sorted(voca)))
        tex.write('\n' + templates['postvoca'])

    tex.write(templates['post'])

    tex.close()

    return tex.name

def generate_pdf(passages, include_voca, combine_voca, clearpage_before_voca,
        large_text, larger_text, tex, pdf, templates, quiet=False):
    tex = generate_tex(passages, include_voca, combine_voca,
            clearpage_before_voca, large_text, larger_text, tex, templates)

    path, filename = os.path.split(pdf)
    jobname, _ = os.path.splitext(filename)

    cmd = ['xelatex']
    if path != '':
        cmd.append('-output-directory')
        cmd.append(path)
    cmd.append('-jobname')
    cmd.append(jobname)
    cmd.append(tex)

    if quiet:
        null = open(os.devnull, 'wb')
        subprocess.call(cmd, stdout=null, stderr=null)
    else:
        subprocess.run(cmd)

    return tex, pdf

def main():
    parser = ArgumentParser(
            description='LaTeX reader generator for Biblical Hebrew',
            formatter_class=RawTextHelpFormatter)

    p_tex = parser.add_argument_group('TeX template options')
    p_tex.add_argument('--pre-tex', type=FileType('r', encoding='utf-8'),
            metavar='FILE', default=open('pre.tex', encoding='utf-8'),
            help='TeX file to prepend to output')
    p_tex.add_argument('--post-tex', type=FileType('r', encoding='utf-8'),
            metavar='FILE', default=open('post.tex', encoding='utf-8'),
            help='TeX file to append to output')
    p_tex.add_argument('--pre-text-tex', type=FileType('r', encoding='utf-8'),
            metavar='FILE', default=open('pretext.tex', encoding='utf-8'),
            help='TeX file to prepend to texts')
    p_tex.add_argument('--post-text-tex', type=FileType('r', encoding='utf-8'),
            metavar='FILE', default=open('posttext.tex', encoding='utf-8'),
            help='TeX file to append to texts')
    p_tex.add_argument('--pre-voca-tex', type=FileType('r', encoding='utf-8'),
            metavar='FILE', default=open('prevoca.tex', encoding='utf-8'),
            help='TeX file to prepend to word list')
    p_tex.add_argument('--post-voca-tex', type=FileType('r', encoding='utf-8'),
            metavar='FILE', default=open('postvoca.tex', encoding='utf-8'),
            help='TeX file to append to word list')

    p_output = parser.add_argument_group('Output options')
    p_output.add_argument('--txt', type=FileType('w', encoding='utf-8'),
            metavar='FILE', help='File to write plain text output to')
    p_output.add_argument('--tex', type=FileType('w', encoding='utf-8'),
            metavar='FILE', help='File to write XeLaTeX output to')
    p_output.add_argument('--pdf',
            metavar='FILE', help='The output PDF file')

    p_misc = parser.add_argument_group('Miscellaneous options')
    p_misc.add_argument('--large-text', dest='large_text', action='store_true',
            help='Use large font and more line spacing for text')
    p_misc.add_argument('--exclude-voca', dest='include_voca', action='store_false',
            help='Do not generate any vocabulary lists')
    p_misc.add_argument('--combine-voca', action='store_true',
            help='Use one vocabulary list for all passages')
    p_misc.add_argument('--clearpage-before-voca', action='store_true',
            help='Start a new page before vocabulary lists')

    parser.add_argument('passages', metavar='PASSAGE', nargs='*',
            help=textwrap.dedent('''\
            The passages to include.
            Examples of correct input are:\n
            - Psalms 1
            - Exodus 3:15
            - Genesis 1-2:3
            - Genesis 2:4-11 (NB: the 11 is the chapter!)
            - 1 Kings 17:7-end
            - Job 38:1-bookend'''))

    args = parser.parse_args()

    if args.pdf is None and args.txt is None and args.tex is None:
        print('At least one of --txt, --tex, or --pdf must be given.')
        sys.exit(1)

    if args.tex is None and args.pdf is not None:
        tex = tempfile.mkstemp(suffix='.tex', prefix='reader')
        args.tex = open(tex[1], 'w', encoding='utf-8')

    print('Loading data...')
    load_verse_nodes()

    if len(args.passages) == 0:
        print('No passages given, not doing anything')
        return

    print('Generating reader...')
    try:
        if args.txt is not None:
            file = generate_txt(args.passages, args.include_voca, args.combine_voca, args.txt)
            print('Plain text written to', file)

        templates = {}
        if args.tex is not None:
            templates['pre'] = args.pre_tex.read()
            templates['post'] = args.post_tex.read()
            templates['pretext'] = args.pre_text_tex.read()
            templates['posttext'] = args.post_text_tex.read()
            templates['prevoca'] = args.pre_voca_tex.read()
            templates['postvoca'] = args.post_voca_tex.read()

        if args.pdf is not None:
            tex, pdf = generate_pdf(args.passages, args.include_voca,
                    args.combine_voca, args.clearpage_before_voca,
                    args.large_text, False, args.tex, args.pdf, templates)
            print('XeLaTeX written to', tex)
            print('PDF written to', pdf)
        elif args.tex is not None:
            tex = generate_tex(args.passages, args.include_voca,
                    args.combine_voca, args.clearpage_before_voca,
                    args.large_text, False, args.tex, templates)
            print('XeLaTeX written to', tex)
    except Exception as e:
        print(e)
        sys.exit(1)

if __name__ == '__main__':
    main()
