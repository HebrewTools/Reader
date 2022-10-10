FROM debian:buster-slim

RUN mkdir -p /usr/src/app
COPY texlive.profile /tmp/texlive.profile

ENV PATH="/usr/local/texlive/2020/bin/x86_64-linux:${PATH}"
WORKDIR /usr/src/app

RUN apt-get update -qq &&\
	apt-get upgrade -qq &&\
	apt-get install -qq build-essential curl fontconfig perl python3-dev python3-setuptools subversion libffi-dev libfontconfig1 python3 tar &&\
	svn export https://github.com/ETCBC/bhsa/trunk/tf/c /bhsa/c &&\
	cd /tmp &&\
	curl -L http://mirrors.ctan.org/systems/texlive/tlnet/install-tl-unx.tar.gz | tar xz &&\
	cd install-tl-* &&\
	./install-tl -repository http://mirrors.ctan.org/systems/texlive/tlnet -profile /tmp/texlive.profile &&\
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
		relsize \
		setspace \
		tools \
		xetex \
		zref &&\
	mktexfmt xelatex.fmt &&\
	curl -H 'User-Agent: stop checking' -L http://www.sbl-site.org/Fonts/SBL_Hbrw.ttf > /usr/local/share/fonts/SBL_Hbrw.ttf &&\
	fc-cache

RUN svn export https://github.com/ETCBC/peshitta/trunk/tf/0.2 /syriac/c

COPY setup.py README.md /usr/src/app/

RUN cd /usr/src/app && python3 setup.py install
RUN cd /usr/src/app && mkdir data

COPY hebrewreader.py hebrewreaderserver.py collectcontexts.py minitf.py *.html /usr/src/app/
RUN cd /usr/src/app && ./collectcontexts.py --bhsa /bhsa --module c --lang hebrew
RUN cd /usr/src/app && ./collectcontexts.py --bhsa /syriac --module c --lang syriac


COPY NotoSansSyriac-Regular.ttf /usr/local/share/fonts/syriac_2.ttf

RUN fc-cache -f && rm -rf /var/cache/*

COPY *.tex /usr/src/app/

ENTRYPOINT ["./hebrewreaderserver.py"]
CMD []