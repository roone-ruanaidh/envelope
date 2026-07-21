PYTHON ?= python3
BASE_URL ?= http://127.0.0.1:8765
SERVICE_COMMAND ?=
CANDIDATE_ROOT ?=
CANDIDATE_COMPLETION ?=
RUN_REPORT ?= build/candidate-acceptance.json
RUN_MODULE = $(PYTHON) -B -I -c 'import runpy,sys;sys.path.insert(0,".");module=sys.argv.pop(1);runpy.run_module(module,run_name="__main__")'

.PHONY: verify verify-dispatch verify-evaluator verify-isolation rerun

verify:
	@if [ -z "$(SERVICE_COMMAND)" ]; then \
		echo "SERVICE_COMMAND is required for behavioral verification (including restart)." >&2; \
		echo "Example: make verify BASE_URL=http://127.0.0.1:8765 SERVICE_COMMAND='python3 -m candidate_service'" >&2; \
		exit 2; \
	fi
	$(RUN_MODULE) evaluator.acceptance \
		--base-url "$(BASE_URL)" \
		--service-command "$(SERVICE_COMMAND)"

verify-evaluator:
	$(RUN_MODULE) evaluator.verify_evaluator --json-report build/evaluator-validation.json

verify-dispatch:
	$(PYTHON) -B -I reproduction/verify_dispatch.py --json-report build/dispatch-validation.json
	$(PYTHON) -B -I reproduction/verify_transfer_envelope.py
	$(PYTHON) -B -I reproduction/verify_evaluator_boundary_test.py
	$(PYTHON) -B -I reproduction/collect_evaluator_guest_test.py

verify-isolation:
	$(PYTHON) -B -I reproduction/verify_isolated_runtime.py build/isolation-validation.json

rerun:
	@if [ -z "$(CANDIDATE_ROOT)" ] || [ -z "$(CANDIDATE_COMPLETION)" ]; then \
		echo "CANDIDATE_ROOT and CANDIDATE_COMPLETION are required." >&2; \
		exit 2; \
	fi
	$(RUN_MODULE) evaluator.rerun \
		--candidate-root "$(CANDIDATE_ROOT)" \
		--candidate-completion "$(CANDIDATE_COMPLETION)" \
		--report "$(RUN_REPORT)"
