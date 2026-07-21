.PHONY: typecheck

export PATH := $(CURDIR)/.venv/bin:$(PATH)

typecheck:
	python3 -m mypy --config-file public/contract/mypy.v1.ini .
