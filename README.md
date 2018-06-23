# Reader

A tool to generate Biblical Hebrew *readers*. A reader contains a number of
texts, joined with a vocabulary containing exactly those lemmas that occur in
the text.

This tool relies on [text-fabric][] for accessing the Hebrew Bible, and on the
data in the [BHSA][].

## Installation

Make sure that you have Python 3 and XeLaTeX installed.

```bash
$ pip3 install text-fabric
$ git clone https://github.com/HebrewTools/Reader
$ git clone https://github.com/ETCBC/bhsa ~/Downloads/etcbc/bhsa
```

## Usage

To get a reader for Genesis:

```
./hebrewreader.py \
  --bhsa ~/Downloads/etcbc/bhsa/tf --module c \
  --pdf genesis.pdf \
  Genesis
```

Instead of `Genesis`, you can also specify passages, e.g. `Psalms 1`, `Exodus
3:15`, `1 Kings 17:7-end` or `Job 38:1-bookend`.

You can also specify multiple passages:

```
./hebrewreader.py \
  --bhsa ~/Downloads/etcbc/bhsa/tf --module c \
  --pdf job-fragments.pdf \
  'Job 28' 'Job 38:1-38'
```

When you combine multiple passages, you can add `--combine-voca` to include one
vocabulary list at the end of the document, rather than separate lists after
each passage.

## Author &amp; License

Copyright &copy; 2018&ndash;present Camil Staps.
Licensed under MIT; see the [LICENSE](/LICENSE) file.

[text-fabric]: https://github.com/DANS-Labs/text-fabric
[BHSA]: https://github.com/ETCBC/bhsa
