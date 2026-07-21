"""A deliberately small validator for canonical OpenAPI response schemas.

The evaluator has no runtime dependencies.  It resolves the response subset
directly from the checked-in human-owned OpenAPI document, so a copied schema
cannot silently drift from the public contract.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping
from uuid import UUID


class SchemaViolation(AssertionError):
    """Raised when an HTTP response is outside the declared OpenAPI shape."""


JSONSchema = Mapping[str, Any]
CANONICAL_OPENAPI_PATH = Path(__file__).resolve().parents[1] / "public" / "contract" / "openapi.v1.json"
SUPPORTED_SCHEMA_KEYS = frozenset(
    {
        "additionalProperties",
        "allOf",
        "anyOf",
        "const",
        "enum",
        "format",
        "maxLength",
        "maximum",
        "minLength",
        "minimum",
        "oneOf",
        "pattern",
        "properties",
        "required",
        "type",
    }
)


def _matches_type(value: Any, expected: str) -> bool:
    if expected == "null":
        return value is None
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    raise RuntimeError(f"unsupported schema type {expected!r}")


def validate_json(value: Any, schema: JSONSchema, path: str = "$") -> None:
    """Validate a value against the JSON Schema constructs used by the contract."""

    unsupported = set(schema) - SUPPORTED_SCHEMA_KEYS
    if unsupported:
        raise RuntimeError(f"unsupported contract schema keywords at {path}: {sorted(unsupported)!r}")

    if "allOf" in schema:
        for alternative in schema["allOf"]:
            validate_json(value, alternative, path)

    alternatives_key = "oneOf" if "oneOf" in schema else "anyOf" if "anyOf" in schema else None
    if alternatives_key is not None:
        errors: list[str] = []
        matches = 0
        for alternative in schema[alternatives_key]:
            try:
                validate_json(value, alternative, path)
            except SchemaViolation as exc:
                errors.append(str(exc))
            else:
                matches += 1
        valid_count = matches == 1 if alternatives_key == "oneOf" else matches >= 1
        if not valid_count:
            raise SchemaViolation(
                f"{path}: expected {'exactly one' if alternatives_key == 'oneOf' else 'at least one'} "
                f"schema alternative, got {matches}; "
                + "; ".join(errors)
            )

    if "const" in schema and value != schema["const"]:
        raise SchemaViolation(f"{path}: expected constant {schema['const']!r}, got {value!r}")

    declared_type = schema.get("type")
    if declared_type is not None:
        allowed = [declared_type] if isinstance(declared_type, str) else declared_type
        if not any(_matches_type(value, item) for item in allowed):
            raise SchemaViolation(f"{path}: expected type {allowed!r}, got {type(value).__name__}")

    if "enum" in schema and value not in schema["enum"]:
        raise SchemaViolation(f"{path}: {value!r} is not in {schema['enum']!r}")

    if isinstance(value, str):
        minimum_length = schema.get("minLength")
        if minimum_length is not None and len(value) < minimum_length:
            raise SchemaViolation(f"{path}: string is shorter than {minimum_length}")
        maximum_length = schema.get("maxLength")
        if maximum_length is not None and len(value) > maximum_length:
            raise SchemaViolation(f"{path}: string is longer than {maximum_length}")
        pattern = schema.get("pattern")
        if pattern is not None and re.search(pattern, value) is None:
            raise SchemaViolation(f"{path}: string does not match pattern {pattern!r}")
        string_format = schema.get("format")
        if string_format == "uuid":
            try:
                parsed = UUID(value)
            except (ValueError, AttributeError) as exc:
                raise SchemaViolation(f"{path}: expected UUID string") from exc
            if str(parsed) != value:
                raise SchemaViolation(f"{path}: UUID must use canonical lowercase form")
        elif string_format is not None:
            raise RuntimeError(f"unsupported string format {string_format!r} at {path}")

    if isinstance(value, int) and not isinstance(value, bool):
        numeric_format = schema.get("format")
        if numeric_format not in {None, "int64"}:
            raise RuntimeError(f"unsupported integer format {numeric_format!r} at {path}")
        minimum = schema.get("minimum")
        if minimum is not None and value < minimum:
            raise SchemaViolation(f"{path}: {value} is less than minimum {minimum}")
        maximum = schema.get("maximum")
        if maximum is not None and value > maximum:
            raise SchemaViolation(f"{path}: {value} is greater than maximum {maximum}")

    if isinstance(value, dict):
        required = schema.get("required", [])
        missing = [name for name in required if name not in value]
        if missing:
            raise SchemaViolation(f"{path}: missing required properties {missing!r}")
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            extra = sorted(set(value) - set(properties))
            if extra:
                raise SchemaViolation(f"{path}: undeclared properties {extra!r}")
        for name, child in properties.items():
            if name in value:
                validate_json(value[name], child, f"{path}.{name}")


OPERATION_LOCATIONS: dict[str, tuple[str, str]] = {
    "health": ("get", "/healthz"),
    "clock_get": ("get", "/_evaluator/clock"),
    "clock_put": ("put", "/_evaluator/clock"),
    "submit": ("post", "/v1/jobs"),
    "get_job": ("get", "/v1/jobs/{job_id}"),
    "claim": ("post", "/v1/leases"),
    "heartbeat": ("post", "/v1/jobs/{job_id}/heartbeat"),
    "complete": ("post", "/v1/jobs/{job_id}/complete"),
    "fail": ("post", "/v1/jobs/{job_id}/fail"),
}


def _json_pointer(document: Mapping[str, Any], reference: str) -> Any:
    if not reference.startswith("#/"):
        raise RuntimeError(f"canonical OpenAPI contains non-local reference {reference!r}")
    value: Any = document
    for raw_part in reference[2:].split("/"):
        part = raw_part.replace("~1", "/").replace("~0", "~")
        if not isinstance(value, dict) or part not in value:
            raise RuntimeError(f"canonical OpenAPI has unresolved reference {reference!r}")
        value = value[part]
    return value


def _resolve(value: Any, document: Mapping[str, Any], stack: tuple[str, ...] = ()) -> Any:
    if isinstance(value, list):
        return [_resolve(item, document, stack) for item in value]
    if not isinstance(value, dict):
        return value
    if "$ref" in value:
        reference = value["$ref"]
        if not isinstance(reference, str):
            raise RuntimeError("canonical OpenAPI $ref must be a string")
        if reference in stack:
            raise RuntimeError(f"canonical OpenAPI has recursive schema reference {reference!r}")
        target = _json_pointer(document, reference)
        siblings = {key: item for key, item in value.items() if key != "$ref"}
        if siblings:
            return {
                "allOf": [
                    _resolve(target, document, stack + (reference,)),
                    _resolve(siblings, document, stack),
                ]
            }
        return _resolve(target, document, stack + (reference,))
    return {key: _resolve(item, document, stack) for key, item in value.items()}


def _assert_supported_schema(schema: JSONSchema, path: str) -> None:
    unsupported = set(schema) - SUPPORTED_SCHEMA_KEYS
    if unsupported:
        raise RuntimeError(f"unsupported contract schema keywords at {path}: {sorted(unsupported)!r}")
    properties = schema.get("properties", {})
    if not isinstance(properties, dict):
        raise RuntimeError(f"contract schema properties at {path} must be an object")
    additional_properties = schema.get("additionalProperties")
    if additional_properties is not None and not isinstance(additional_properties, bool):
        raise RuntimeError(
            f"contract schema additionalProperties at {path} must be a boolean"
        )
    for name, child in properties.items():
        if not isinstance(child, dict):
            raise RuntimeError(f"contract property schema {path}.{name} must be an object")
        _assert_supported_schema(child, f"{path}.{name}")
    for keyword in ("allOf", "anyOf", "oneOf"):
        alternatives = schema.get(keyword, [])
        if not isinstance(alternatives, list):
            raise RuntimeError(f"contract schema {keyword} at {path} must be an array")
        for index, child in enumerate(alternatives):
            if not isinstance(child, dict):
                raise RuntimeError(f"contract schema {keyword}[{index}] at {path} must be an object")
            _assert_supported_schema(child, f"{path}.{keyword}[{index}]")
    pattern = schema.get("pattern")
    if pattern is not None:
        try:
            re.compile(pattern)
        except re.error as exc:
            raise RuntimeError(f"invalid contract regex at {path}: {pattern!r}") from exc
    schema_format = schema.get("format")
    if schema_format not in {None, "int64", "uuid"}:
        raise RuntimeError(f"unsupported contract format at {path}: {schema_format!r}")


@lru_cache(maxsize=1)
def canonical_openapi() -> dict[str, Any]:
    """Load the human-owned contract, which is the evaluator's schema authority."""

    def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate object key {key!r}")
            result[key] = value
        return result

    try:
        raw = json.loads(
            CANONICAL_OPENAPI_PATH.read_text(encoding="utf-8"),
            object_pairs_hook=reject_duplicate_keys,
        )
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise RuntimeError(f"cannot load canonical OpenAPI contract at {CANONICAL_OPENAPI_PATH}") from exc
    if not isinstance(raw, dict):
        raise RuntimeError("canonical OpenAPI contract must be a JSON object")
    if raw.get("openapi") != "3.1.0":
        raise RuntimeError("canonical OpenAPI contract must declare OpenAPI 3.1.0")
    info = raw.get("info")
    if not isinstance(info, dict) or info.get("version") != "1.0.0":
        raise RuntimeError("canonical OpenAPI contract version must be 1.0.0")
    return raw


@lru_cache(maxsize=None)
def canonical_response_schemas(operation: str) -> dict[int, JSONSchema | None]:
    """Resolve status-indexed schemas from the checked-in canonical contract."""

    document = canonical_openapi()
    try:
        method, path = OPERATION_LOCATIONS[operation]
        operation_object = document["paths"][path][method]
        raw_responses = operation_object["responses"]
    except (KeyError, TypeError) as exc:
        raise RuntimeError(f"canonical OpenAPI omits operation {operation!r}") from exc
    if not isinstance(raw_responses, dict):
        raise RuntimeError(f"canonical OpenAPI responses for {operation!r} must be an object")
    schemas: dict[int, JSONSchema | None] = {}
    for raw_status, raw_response in raw_responses.items():
        if not isinstance(raw_status, str) or not raw_status.isdigit():
            raise RuntimeError(f"canonical OpenAPI {operation!r} uses unsupported status {raw_status!r}")
        status = int(raw_status)
        response = _resolve(raw_response, document)
        if not isinstance(response, dict):
            raise RuntimeError(f"canonical OpenAPI response {operation!r}/{status} is invalid")
        content = response.get("content")
        if content is None:
            schemas[status] = None
            continue
        if not isinstance(content, dict) or "application/json" not in content:
            raise RuntimeError(
                f"canonical OpenAPI response {operation!r}/{status} lacks application/json"
            )
        media = content["application/json"]
        if not isinstance(media, dict) or "schema" not in media:
            raise RuntimeError(f"canonical OpenAPI response {operation!r}/{status} lacks schema")
        resolved_schema = _resolve(media["schema"], document)
        if not isinstance(resolved_schema, dict):
            raise RuntimeError(f"canonical OpenAPI schema {operation!r}/{status} is invalid")
        schemas[status] = resolved_schema

    for status, schema in schemas.items():
        if status == 204 and schema is not None:
            raise RuntimeError(f"canonical OpenAPI {operation!r}/204 unexpectedly has a body schema")
        if status != 204 and schema is None:
            raise RuntimeError(f"canonical OpenAPI {operation!r}/{status} lacks a body schema")
    return schemas


def assert_contract_alignment() -> None:
    """Fail closed unless the evaluator covers every contracted operation."""

    expected_locations = set(OPERATION_LOCATIONS.values())
    if len(expected_locations) != len(OPERATION_LOCATIONS):
        raise RuntimeError("multiple evaluator operations map to the same contract operation")

    document = canonical_openapi()
    declared_locations: set[tuple[str, str]] = set()
    for path, path_item in document.get("paths", {}).items():
        if not isinstance(path_item, dict):
            raise RuntimeError(f"canonical OpenAPI path item {path!r} must be an object")
        for method in ("get", "put", "post", "delete", "patch", "options", "head", "trace"):
            if method in path_item:
                declared_locations.add((method, path))
    if declared_locations != expected_locations:
        raise RuntimeError(
            "evaluator/contract operation drift: evaluator "
            f"{sorted(expected_locations)!r}, contract {sorted(declared_locations)!r}"
        )
    for operation in sorted(OPERATION_LOCATIONS):
        method, path = OPERATION_LOCATIONS[operation]
        operation_object = document["paths"][path][method]
        request_body = operation_object.get("requestBody")
        if request_body is not None:
            resolved_body = _resolve(request_body, document)
            try:
                request_schema = resolved_body["content"]["application/json"]["schema"]
            except (KeyError, TypeError) as exc:
                raise RuntimeError(
                    f"canonical OpenAPI request body for {operation!r} lacks an application/json schema"
                ) from exc
            _assert_supported_schema(request_schema, f"request:{operation}")
        for status, response_schema in canonical_response_schemas(operation).items():
            if response_schema is not None:
                _assert_supported_schema(response_schema, f"response:{operation}:{status}")
