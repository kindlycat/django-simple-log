.PHONY: clean, build

clean:
	rm -r build dist *.egg-info

build:
	python setup.py sdist
	python setup.py bdist_wheel
