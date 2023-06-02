release:
	standard-version

publish: clean
	git push --follow-tags
	python setup.py sdist bdist_wheel
	twine upload dist/*

clean:
	rm -rf dist

test:
	poetry run python ./runtests.py
