.PHONY: test lint build docs

test:
	python -m pytest tests

lint:
	pre-commit run --all-files

build:
	python -m build

docs:
	npx antora antora-playbook.yml
