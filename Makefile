release:
	standard-version

publish: clean
	python -m build
	twine upload dist/*
	git push --follow-tags

clean:
	rm -rf dist

lint:
	ruff check modeltranslation
	ruff format --check modeltranslation *.py

typecheck:
	mypy --pretty modeltranslation
