FROM debian:buster-slim

COPY texlive.profile /tmp/texlive.profile

ENV PATH="/usr/local/texlive/2020/bin/x86_64-linux:${PATH}"
RUN apt-get update -qq &&\
	apt-get upgrade -qq &&\
	apt-get install -qq curl libfontconfig1 fontconfig tar perl python3 python3-setuptools python3-dev build-essential subversion &&\
	svn export https://github.com/ETCBC/bhsa/trunk/tf/c /bhsa/c &&\
	curl -L http://ctan.cs.uu.nl/systems/texlive/tlnet/install-tl-unx.tar.gz | tar xz &&\
	cd install-tl-* &&\
	cat /tmp/texlive.profile &&\
	./install-tl -repository http://ctan.cs.uu.nl/systems/texlive/tlnet -profile /tmp/texlive.profile &&\
	cd .. &&\
	rm -rf install-tl-* &&\
	tlmgr install \
		atbegshi \
		bidi \
		etexcmds \
		geometry \
		graphics \
		kvdefinekeys \
		kvsetkeys \
		lm \
		ltxcmds \
		oberdiek \
		polyglossia \
		setspace \
		tools \
		xetex \
		zref &&\
	mktexfmt xelatex.fmt &&\
	curl -H 'User-Agent: stop checking' -L http://www.sbl-site.org/Fonts/SBL_Hbrw.ttf > /usr/local/share/fonts/SBL_Hbrw.ttf &&\
	fc-cache

RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app
COPY *.md *.py *.tex *.html /usr/src/app/
RUN python3 setup.py install &&\
	mkdir data &&\
	./collectcontexts.py --bhsa /bhsa --module c

ENTRYPOINT ["./hebrewreaderserver.py"]
CMD []
