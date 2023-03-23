release:
	standard-version

publish: clean
	python setup.py sdist bdist_wheel
	twine upload dist/*
	git push --follow-tags

clean:
	rm -rf dist

test:
	poetry run python ./runtests.py
