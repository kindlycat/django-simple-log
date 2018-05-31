.PHONY: clean, build, flake

clean:
	rm -rf build dist *.egg-info

build:
	python setup.py sdist
	python setup.py bdist_wheel
