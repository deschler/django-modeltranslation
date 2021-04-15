release:
	standard-version

publish: clean
	python setup.py sdist
	twine upload dist/*

clean:
	rm -rf dist

test:
	poetry run python ./runtests.py
