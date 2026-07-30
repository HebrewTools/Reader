FROM debian:trixie-slim

ENV PATH="/usr/local/texlive/2026/bin/x86_64-linux:${PATH}"
RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app

RUN export INSTALL_PACKAGES="build-essential curl fontconfig git perl perl-modules" &&\
	export PACKAGES="libffi-dev libfontconfig1 python3 python3-pip tar" &&\
	apt-get update -qq &&\
	apt-get upgrade -qq &&\
	apt-get install -qq $INSTALL_PACKAGES $PACKAGES &&\
	rm -rf /var/lib/apt/lists/* &&\
	git clone -n --depth=1 --filter=tree:0 https://github.com/ETCBC/bhsa.git /bhsa &&\
	cd /bhsa &&\
	git sparse-checkout set --no-cone tf/c &&\
	git checkout

RUN curl -L https://www.sbl-site.org/wp-content/themes/basket/fonts/bib-fonts/SBL_Hbrw.ttf > /usr/local/share/fonts/SBL_Hbrw.ttf &&\
	fc-cache

COPY requirements.txt /usr/src/app
RUN cd /usr/src/app &&\
	pip3 install --break-system-packages -r requirements.txt

COPY README.md collectcontexts.py common.py minitf.py /usr/src/app/
RUN cd /usr/src/app &&\
	mkdir data &&\
	./collectcontexts.py --bhsa /bhsa/tf --module c

COPY texlive.profile /tmp/texlive.profile
RUN cd /tmp &&\
	curl -L http://mirrors.ctan.org/systems/texlive/tlnet/install-tl-unx.tar.gz | tar xz &&\
	#curl -L https://nl.mirrors.cicku.me/ctan/systems/texlive/tlnet/install-tl-unx.tar.gz | tar xz &&\
	cd install-tl-* &&\
	./install-tl -repository http://mirrors.ctan.org/systems/texlive/tlnet -profile /tmp/texlive.profile &&\
	#./install-tl -repository https://nl.mirrors.cicku.me/ctan/systems/texlive/tlnet -profile /tmp/texlive.profile &&\
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
	mktexfmt xelatex.fmt
