# Reader

A tool to generate Biblical Hebrew *readers*. A reader contains a number of
texts, joined with a vocabulary containing exactly those lemmas that occur in
the text.

The tool can also be used at [reader.hebrewtools.org][live].

This tool relies on [text-fabric][] for accessing the Hebrew Bible, and on the
data in the [BHSA][].

## Installation

Make sure that you have Python 3 and XeLaTeX installed.

```bash
$ pip3 install text-fabric
$ git clone https://github.com/HebrewTools/Reader
$ svn export https://github.com/ETCBC/bhsa/trunk/tf/c /tmp/bhsa
$ cd Reader
$ mkdir data
$ ./collectcontexts.py --bhsa /tmp --module bhsa
```

## Usage

To get a reader for Genesis:

```
./hebrewreader.py \
  --pdf genesis.pdf \
  Genesis
```

Instead of `Genesis`, you can also specify passages, e.g. `Psalms 1`, `Exodus
3:15`, `1 Kings 17:7-end` or `Job 38:1-bookend`.

You can also specify multiple passages:

```
./hebrewreader.py \
  --pdf job-fragments.pdf \
  'Job 28' 'Job 38:1-38'
```

When you combine multiple passages, you can add `--combine-voca` to include one
vocabulary list at the end of the document, rather than separate lists after
each passage.

See `./hebrewreader.py --help` for more options.

## Web server

The easiest way to access the reader is using the web server. It is not needed
to install it; simply go to [reader.hebrewtools.org][live].

To run the web server locally, run `./runserver.sh`. It is distributed as a
Docker app, so besides Docker you will not need to have anything installed.

It may be that the LaTeX installation in the Docker image fails due to
contemporaneous updates to the TeX Live registry. In that case, run
`./runserver.sh` again later.

## Building &amp; deploying (Docker)

Normally you can just build the CLI image and use that, for instance:

```
docker build -t camilstaps/hebrew-reader:cli -f Dockerfile.cli .
docker run --rm -it camilstaps/hebrew-reader:cli --txt - 'Genesis 1'
```

Note that LaTeX/PDF output are a bit more complicated as the Docker container
normally doesn't have access to your file system. The plain text output works
as it can just output to the terminal.

For the server, use:

```
docker build -t camilstaps/hebrew-reader:server -f Dockerfile.server .
docker run --network host --rm -it camilstaps/hebrew-reader:server
```

You can then access it at http://localhost:19419/.

During development you need to rerun both the `build` and the `run` command
after modifying files.

If you modify the core of the app (e.g. collectcontexts.py), rebuild the base
image first:

```
docker build -t camilstaps/hebrew-reader:base .
```

Deploying can be done with `runserver.sh`.

## Author &amp; License

Copyright &copy; 2018&ndash;present Camil Staps.
Licensed under MIT; see the [LICENSE](/LICENSE) file.

[live]: https://reader.hebrewtools.org
[text-fabric]: https://github.com/DANS-Labs/text-fabric
[BHSA]: https://github.com/ETCBC/bhsa
