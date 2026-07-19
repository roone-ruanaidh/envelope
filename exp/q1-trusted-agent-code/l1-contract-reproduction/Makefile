PYTHON ?= python3
BASE_URL ?= http://127.0.0.1:8765
SERVICE_COMMAND ?=
CANDIDATE_ROOT ?=
CANDIDATE_MODULE ?=
RUN_REPORT ?= build/candidate-acceptance.json

.PHONY: verify verify-evaluator rerun

verify:
	@if [ -z "$(SERVICE_COMMAND)" ]; then \
		echo "SERVICE_COMMAND is required for behavioral verification (including restart)." >&2; \
		echo "Example: make verify BASE_URL=http://127.0.0.1:8765 SERVICE_COMMAND='python3 -m candidate_service'" >&2; \
		exit 2; \
	fi
	$(PYTHON) -m evaluator.acceptance \
		--base-url "$(BASE_URL)" \
		--service-command "$(SERVICE_COMMAND)"

verify-evaluator:
	$(PYTHON) -m evaluator.verify_evaluator --json-report build/evaluator-validation.json

rerun:
	@if [ -z "$(CANDIDATE_ROOT)" ] || [ -z "$(CANDIDATE_MODULE)" ]; then \
		echo "CANDIDATE_ROOT and CANDIDATE_MODULE are required." >&2; \
		exit 2; \
	fi
	$(PYTHON) -m evaluator.rerun \
		--candidate-root "$(CANDIDATE_ROOT)" \
		--candidate-module "$(CANDIDATE_MODULE)" \
		--report "$(RUN_REPORT)"
