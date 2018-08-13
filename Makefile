.PHONY: help, clean, build, docs

help:
	@cat $(MAKEFILE_LIST)

clean:
	rm -rf build dist *.egg-info

build:
	python setup.py sdist
	python setup.py bdist_wheel

docs:
	make -C ./docs html
