release:
	standard-version

publish: clean
	python setup.py sdist
	twine upload dist/*

clean:
	rm -rf dist
