FROM debian:bookworm-slim

RUN mkdir -p /usr/src/app
COPY *.md *.py *.tex *.html /usr/src/app/
COPY texlive.profile /tmp/texlive.profile

ENV PATH="/usr/local/texlive/2025/bin/x86_64-linux:${PATH}"
WORKDIR /usr/src/app

RUN export INSTALL_PACKAGES="build-essential curl fontconfig git perl perl-modules python3-dev" &&\
	export PACKAGES="libffi-dev libfontconfig1 python3 python3-setuptools tar" &&\
	apt-get update -qq &&\
	apt-get upgrade -qq &&\
	apt-get install -qq $INSTALL_PACKAGES $PACKAGES &&\
	git clone -n --depth=1 --filter=tree:0 https://github.com/ETCBC/bhsa.git /bhsa &&\
	cd /bhsa &&\
	git sparse-checkout set --no-cone tf/c &&\
	git checkout &&\
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
	fc-cache &&\
	cd /usr/src/app &&\
	SETUPTOOLS_USE_DISTUTILS=stdlib python3 setup.py install &&\
	mkdir data &&\
	./collectcontexts.py --bhsa /bhsa/tf --module c &&\
	apt-get remove -qq $INSTALL_PACKAGES &&\
	apt-get -qq autoremove &&\
	rm -rf /var/lib/apt/lists/*

ENTRYPOINT ["./hebrewreaderserver.py"]
CMD []
