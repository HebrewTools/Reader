#!/usr/bin/env python3

from argparse import ArgumentParser, FileType, RawTextHelpFormatter
import re
import subprocess
import sys
import textwrap

from tf.fabric import Fabric

PASSAGE_RGX = (
    r'^(?P<book>(?:\d )?[a-zA-Z ]+) '
    r'(?P<startchap>\d+)(?::(?P<startverse>\d+))?'
    r'(?:-(?P<endref>(?P<endchap>\d+)(?::(?P<endverse>\d+))?|(?:book)?end))?$'
)

FEATURES = 'g_word_utf8 gloss lex_utf8 otype trailer_utf8 voc_lex_utf8'

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

    if match['endchap'] is None:
        if match['startverse'] is None and match['endref'] is None:
            match['endref'] = 'end'
        else:
            match['endchap'] = match['startchap']
            match['endverse'] = match['startverse']
    elif match['endverse'] is None:
        location = T.nodeFromSection((match['book'], match['endchap'], 1))
        location = L.u(location, otype='chapter')[0]
        location = L.n(location, otype='chapter')[0]
        location = L.p(location, otype='verse')[0]
        _, _, match['endverse'] = T.sectionFromNode(location)

    if match['startverse'] is None:
        match['startverse'] = 1

    if match['endref'] == 'end':
        location = T.nodeFromSection((match['book'], match['startchap']))
        location = L.n(location, otype='chapter')[0]
        location = L.d(location, otype='verse')[0]
        location = L.p(location, otype='verse')[0]
        _, match['endchap'], match['endverse'] = T.sectionFromNode(location)
    elif match['endref'] == 'bookend':
        location = T.nodeFromSection((match['book'],))
        location = L.n(location, otype='book')[0]
        location = L.d(location, otype='verse')[0]
        location = L.p(location, otype='verse')[0]
        _, match['endchap'], match['endverse'] = T.sectionFromNode(location)

    match.pop('endref')
    return match

def verses_in_passage(passage):
    for chap in range(passage['startchap'], passage['endchap']+1):
        start = passage['startverse'] if chap == passage['startchap'] else 1
        if chap == passage['endchap']:
            end = passage['endverse']
        else:
            location = T.nodeFromSection((passage['book'], chap+1))
            location = L.d(location, otype='verse')[0]
            location = L.p(location, otype='verse')[0]
            _, _, end = T.sectionFromNode(location)

        for verse in range(start, end+1):
            yield (passage['book'], chap, verse)

def fix_trailer(trailer):
    return trailer\
            .replace('\n', '')\
            .replace('\u05e1', r'\setuma{}')\
            .replace('\u05e4', r'\petucha{}')

def fix_gloss(gloss):
    if gloss == 'i':
        return 'I'
    return re.sub(r'<(.*)>', r'\\textit{\1}', gloss)

def get_passage_and_words(passage, separate_chapters=True, verse_nos=True):
    text = []
    words = set()

    last_chapter = None
    for verse in verses_in_passage(passage):
        if verse[1] != last_chapter:
            last_chapter = verse[1]
            if separate_chapters:
                text.append('\n')
        node = T.nodeFromSection(verse)
        wordnodes = L.d(node, otype='word')
        thistext = ''
        if verse_nos:
            if verse[2] == 1:
                thistext += r'\rdrchap{%d}' % verse[1]
            thistext += r'\rdrverse{%d} ' % verse[2]
        thiswords = []
        for word in wordnodes:
            thiswords.append(
                    F.g_word_utf8.v(word) +
                    fix_trailer(F.trailer_utf8.v(word)))
            lex = L.u(word, otype='lex')[0]
            words.add((F.lex_utf8.v(word), F.voc_lex_utf8.v(lex), fix_gloss(F.gloss.v(lex))))
        thistext += ''.join(thiswords)
        text.append(thistext)

    return text, sorted(words)

def main():
    parser = ArgumentParser(
            description='LaTeX reader generator for Biblical Hebrew',
            formatter_class=RawTextHelpFormatter)

    p_data = parser.add_argument_group('Data source options')
    p_data.add_argument('--bhsa', '-b', nargs=1, required=True,
            help='Location of the BHSA data')
    p_data.add_argument('--module', '-m', nargs=1, required=True,
            help='Text-fabric module to load')

    p_tex = parser.add_argument_group('TeX template options')
    p_tex.add_argument('--pre-tex', type=FileType('r'), metavar='FILE',
            default=open('pre.tex'), help='TeX file to prepend to output')
    p_tex.add_argument('--post-tex', type=FileType('r'), metavar='FILE',
            default=open('post.tex'), help='TeX file to append to output')
    p_tex.add_argument('--pre-text-tex', type=FileType('r'), metavar='FILE',
            default=open('pretext.tex'), help='TeX file to prepend to texts')
    p_tex.add_argument('--post-text-tex', type=FileType('r'), metavar='FILE',
            default=open('posttext.tex'), help='TeX file to append to texts')
    p_tex.add_argument('--pre-voca-tex', type=FileType('r'), metavar='FILE',
            default=open('prevoca.tex'), help='TeX file to prepend to word list')
    p_tex.add_argument('--post-voca-tex', type=FileType('r'), metavar='FILE',
            default=open('postvoca.tex'), help='TeX file to append to word list')

    p_output = parser.add_argument_group('Output options')
    p_output.add_argument('--output', '-o', type=FileType('w'),
            default=sys.stdout, help='File to write to')
    p_output.add_argument('--pdf', action='store_true',
            help='Compile the generated LaTeX to PDF')

    p_misc = parser.add_argument_group('Miscellaneous options')
    p_misc.add_argument('--combine-voca', action='store_true',
            help='Use one vocabulary list for all passages')

    parser.add_argument('passages', metavar='PASSAGE', nargs='+',
            help=textwrap.dedent('''\
            The passages to include.
            Examples of correct input are:\n
            - Psalm 1
            - Exodus 3:15
            - Genesis 1-2:3
            - 1 Kings 17:7-end
            - Job 38:1-bookend'''))

    args = parser.parse_args()

    TF = Fabric(modules=args.module, locations=args.bhsa, silent=True)
    api = TF.load(FEATURES, silent=True)
    api.makeAvailableIn(globals())

    args.output.write(args.pre_tex.read())

    pretext = args.pre_text_tex.read()
    posttext = args.post_text_tex.read()
    prevoca = args.pre_voca_tex.read()
    postvoca = args.post_voca_tex.read()

    voca = set()

    for passage in args.passages:
        try:
            passage = parse_passage(passage)
        except:
            print('Failed to parse this passage: "{}"'.format(passage))
            sys.exit(1)

        passage_pretty = '{} {}:{} - {}:{}'.format(
            passage['book'].replace('_', ' '),
            passage['startchap'], passage['startverse'],
            passage['endchap'], passage['endverse'])
        print(passage_pretty)
        args.output.write(r'\def\thepassage{%s}' % passage_pretty)

        text, words = get_passage_and_words(passage)

        args.output.write('\n\n' + pretext)
        args.output.write('\n'.join(text))
        args.output.write('\n' + posttext)

        if args.combine_voca:
            voca.update(words)
        else:
            args.output.write('\n\n' + prevoca)
            args.output.write('\\\\\n'.join(r'{\hebrewfont\RL{%s}} \begin{english}%s\end{english}' % (lex,gloss) for _, lex, gloss in words))
            args.output.write('\n' + postvoca)

    if args.combine_voca:
        args.output.write('\n\n' + prevoca)
        args.output.write('\\\\\n'.join(r'{\hebrewfont\RL{%s}} \begin{english}%s\end{english}' % (lex,gloss) for _, lex, gloss in sorted(voca)))
        args.output.write('\n' + postvoca)

    args.output.write(args.post_tex.read())

    if args.pdf:
        if args.output == sys.stdout:
            print('--output must be set to a normal file to use --pdf')
        else:
            args.output.close()
            subprocess.run(['xelatex', args.output.name])

if __name__ == '__main__':
    main()
