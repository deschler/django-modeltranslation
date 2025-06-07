release:
	commit-and-tag-version

publish: build
	twine upload dist/*
	git push --follow-tags

build: clean
	python -m build --installer uv

clean:
	rm -rf dist

lint:
	ruff check modeltranslation
	ruff format --check modeltranslation *.py

typecheck:
	mypy --pretty modeltranslation

sync:
	uv sync --group dev --group lsp --no-install-project

test:
	uv run --no-sync pytest
