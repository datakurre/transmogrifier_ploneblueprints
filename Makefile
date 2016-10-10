BUILDOUT_FILENAME ?= buildout.cfg

BUILDOUT_BIN ?= $(shell command -v buildout || echo 'bin/buildout')
BUILDOUT_ARGS ?= -c $(BUILDOUT_FILENAME)

all: build check

show: $(BUILDOUT_BIN)
	$(BUILDOUT_BIN) $(BUILDOUT_ARGS) annotate

build: $(BUILDOUT_BIN)
	$(BUILDOUT_BIN) $(BUILDOUT_ARGS)

test: bin/test
	bin/test --all

check: test

clean:
	rm -rf .installed bin develop-eggs parts

###

.PHONY: all show build test check dist watch clean

bootstrap-buildout.py:
	curl -k -O https://bootstrap.pypa.io/bootstrap-buildout.py

bin/buildout: bootstrap-buildout.py $(BUILDOUT_FILENAME)
	python bootstrap-buildout.py -c $(BUILDOUT_FILENAME)

bin/test: $(BUILDOUT_BIN) $(BUILDOUT_FILENAME) setup.py
	$(BUILDOUT_BIN) $(BUILDOUT_ARGS) install test
