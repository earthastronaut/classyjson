SHELL=/bin/bash
VERSION=$(shell git describe --tags)
GIT_STATUS_SUMMARY=$(shell git status --porcelain)

# Build distribution
build:
	@echo "Check that directory is clean. Please commit all changes."
	[ "${GIT_STATUS_SUMMARY}" = "" ]  # [ "$$(git status --porcelain)" = "" ]
	git describe --tags > VERSION	
	source dev/bin/activate.sh && python setup.py sdist bdist_wheel

# Clean the build
clean-build:
	rm -rf dist && true
	rm -rf build && true

# Clean up all
clean: clean-build
	find . -type f -name "*.py[co]" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" | xargs rm -r $1
	rm -rf .venv && true

# Run unit tests with coverage
test:
	source dev/bin/activate.sh && test-coverage.sh tests

# Run unit tests with dev
test-dev:
	source dev/bin/activate.sh && test.sh --pdb tests

# Run all linters on python files
lint:
	source dev/bin/activate.sh \
		&& pylint.sh . \
		&& flake8.sh . \
		&& black.sh --check . \
		&& mypy.sh classyjson.py

lint-types:
	source dev/bin/activate.sh \
		&& mypy.sh classyjson.py

# Display version
version:
	@echo ${VERSION}

# Create virtual environment
venv:
	source dev/bin/activate.sh && which python

# Show help
help:
	@echo ""
	@echo "Usage: make <target>"
	@echo "Targets:"
	@grep -E "^[a-z,A-Z,0-9,-]+:.*" Makefile | sort | cut -d : -f 1 | xargs printf '  %s\n'
	@echo ""

.DEFAULT_GOAL=help
.PHONY: build clean-build clean help lint-types lint test-dev test venv version
# echo .PHONY: $(grep -E "^[a-z,A-Z,0-9,-]+:.*" Makefile | sort | cut -d : -f 1 | xargs)
