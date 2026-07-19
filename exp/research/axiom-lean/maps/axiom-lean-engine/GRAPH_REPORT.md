# Graph Report - AxiomMath/axiom-lean-engine@12b1278  (2026-07-18)

## Corpus Check
- Corpus is ~49,464 words - fits in a single context window. You may not need a graph.

## Summary
- 429 nodes · 1374 edges · 24 communities detected
- Extraction: 36% EXTRACTED · 64% INFERRED · 0% AMBIGUOUS · INFERRED: 875 edges (avg confidence: 0.53)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_SDK Types and Errors|SDK Types and Errors]]
- [[_COMMUNITY_Tool Semantics and CLI|Tool Semantics and CLI]]
- [[_COMMUNITY_Async Client Methods|Async Client Methods]]
- [[_COMMUNITY_Endpoint Metadata and CLI|Endpoint Metadata and CLI]]
- [[_COMMUNITY_HTTP Transport and Retry|HTTP Transport and Retry]]
- [[_COMMUNITY_Lean Text Helpers|Lean Text Helpers]]
- [[_COMMUNITY_Strict Proof Verification|Strict Proof Verification]]
- [[_COMMUNITY_Merge and Normalize|Merge and Normalize]]
- [[_COMMUNITY_Lemma Extraction|Lemma Extraction]]
- [[_COMMUNITY_Proof Repair and Simplification|Proof Repair and Simplification]]
- [[_COMMUNITY_Declaration Extraction Flow|Declaration Extraction Flow]]
- [[_COMMUNITY_Axiom Brand Lockup|Axiom Brand Lockup]]
- [[_COMMUNITY_Release and Deployment Drift|Release and Deployment Drift]]
- [[_COMMUNITY_Base Error Type|Base Error Type]]
- [[_COMMUNITY_Runtime Error Classification|Runtime Error Classification]]
- [[_COMMUNITY_Environment Version Selection|Environment Version Selection]]
- [[_COMMUNITY_Comment Removal Tests|Comment Removal Tests]]
- [[_COMMUNITY_Message Position Parsing|Message Position Parsing]]
- [[_COMMUNITY_Axiom Favicon|Axiom Favicon]]
- [[_COMMUNITY_API Key Authentication|API Key Authentication]]
- [[_COMMUNITY_Test Package Documentation|Test Package Documentation]]
- [[_COMMUNITY_Favicon Dark Base|Favicon Dark Base]]
- [[_COMMUNITY_Favicon Middle Facet|Favicon Middle Facet]]
- [[_COMMUNITY_Favicon Upper Facet|Favicon Upper Facet]]

## God Nodes (most connected - your core abstractions)
1. `AxleClient` - 67 edges
2. `AxleIsUnavailable` - 35 edges
3. `AxleInternalError` - 35 edges
4. `AxleInvalidArgument` - 34 edges
5. `AxleRuntimeError` - 34 edges
6. `LeanResourceExceeded` - 34 edges
7. `LeanTimeout` - 34 edges
8. `AxleForbiddenError` - 33 edges
9. `AxleNotFoundError` - 33 edges
10. `AxleConflictError` - 33 edges

## Surprising Connections (you probably didn't know these)
- `Disprove by Proving Negation` --semantically_similar_to--> `Verify Negation Option`  [INFERRED] [semantically similar]
  docs/tools/disprove.md → axle/cli/endpoints.py
- `Unfolded Type Hash Deduplication` --semantically_similar_to--> `Merge Dependency and Conflict Strategy`  [INFERRED] [semantically similar]
  CHANGELOG.md → axle/cli/endpoints.py
- `AXLE Message and okay Semantics` --shares_data_with--> `Messages`  [INFERRED]
  docs/troubleshooting.md → axle/types.py
- `Lean Utility Tool Suite` --shares_data_with--> `ENDPOINTS Catalog`  [INFERRED]
  docs/index.md → axle/cli/endpoints.py
- `Extract and validate theorems.` --uses--> `AxleApiError`  [INFERRED]
  examples/extract_and_validate.py → axle/exceptions.py

## Hyperedges (group relationships)
- **AXLE API Request Lifecycle** — client_tool_method_family, client_run_one, client_call, client_call_attempt, types_transformation_models [EXTRACTED 1.00]
- **Metadata-Driven CLI Flow** — endpoints_catalog, cli_main_create_parser, cli_main_build_request_kwargs, cli_main_run_command, cli_main_output_formatting [EXTRACTED 1.00]
- **Lean Subgoal Extraction Pattern** — endpoints_subgoal_transform_metadata, endpoints_mathlib_extract_goal, client_proof_transform_methods [EXTRACTED 1.00]
- **Goal Lifting into Standalone Lemmas** — have2lemma_tool, sorry2lemma_tool, have2lemma_extract_goal_tactic [EXTRACTED 1.00]
- **Lean File Consolidation Flow** — normalize_tool, merge_tool, rename_tool [EXTRACTED 1.00]
- **Adversarial Proof Verification Alternatives** — verify_proof_tool, verify_proof_lean4checker, verify_proof_comparator, verify_proof_safeverify [EXTRACTED 1.00]
- **Axiom Brand Lockup Composition** — logo_layered_geometric_mark, logo_axiom_wordmark, logo_starting_point_for_reasoning_tagline [EXTRACTED 1.00]
- **Three-Layer Geometric Mark Composition** — favicon_dark_trapezoidal_base, favicon_medium_blue_middle_facet, favicon_pale_blue_upper_facet [EXTRACTED 1.00]

## Communities

### Community 0 - "SDK Types and Errors"
Cohesion: 0.28
Nodes (69): AXLE client for the Lean verification API., Health check; raises AxleApiError subclasses on transport or HTTP errors., Run a single API request., Verify a proof against a formal statement., Extract theorems with dependencies from Lean code.          Deprecated: use extr, Extract all declarations with dependencies from Lean code., Merge multiple Lean files into one., Replace proofs with sorry. (+61 more)

### Community 1 - "Tool Semantics and CLI"
Cohesion: 0.04
Nodes (65): extract_decls Supersedes extract_theorems, Selective Declaration Elaboration, Unfolded Type Hash Deduplication, check Compilation-Only Semantics, Lean 4 Web Playground, Selected Declaration Message Incompleteness, Use verify_proof for Proof Validity, CLI Entrypoint Export (+57 more)

### Community 2 - "Async Client Methods"
Cohesion: 0.09
Nodes (20): main(), Demonstrate basic proof verification., AxleClient, _exc_msg(), _lean_version_key(), _maybe_google_oidc_302_exc(), _client_with_environments(), Tests for the AXLE client response types. (+12 more)

### Community 3 - "Endpoint Metadata and CLI"
Cohesion: 0.11
Nodes (42): CliOutputConfig, EndpointMetadata, InputField, OutputField, Metadata for Axle API endpoints used to generate GUI forms., Generate tool_messages output with tool-specific description., Configuration for CLI output behavior., Definition of an output field from an API endpoint. (+34 more)

### Community 4 - "HTTP Transport and Retry"
Cohesion: 0.07
Nodes (36): HTTP/1.1 aiohttp Transport Choice, AxleClient, AxleClient._call, AxleClient._call_attempt, AxleClient.check_status, Async Context Cleanup, AxleClient.environments, Google OIDC Browser Login Detection (+28 more)

### Community 5 - "Lean Text Helpers"
Cohesion: 0.09
Nodes (28): inline_lean_messages(), Helper utilities for working with AXLE.  This module provides utilities for stri, Inline Lean compiler messages as comments in the source code.      Messages with, Remove comments from Lean code, including multi-line comments.      Args:, remove_comments(), Tests for AXLE helper functions., Messages with and without endPos should both work., Comment-like syntax inside strings should not be removed. (+20 more)

### Community 6 - "Strict Proof Verification"
Cohesion: 0.1
Nodes (20): AxleClient.verify_proof Invocation, Verification Result Diagnostics, VerifyProofResponse Deserialization Test, VerifyProofResponse.from_response, mock_verify_response(), Pytest configuration and fixtures for AXLE tests., Mock response for verify_proof endpoint., Candidate Proof Implementation (+12 more)

### Community 7 - "Merge and Normalize"
Cohesion: 0.11
Nodes (18): Conflict Resolution by Renaming, Error-Free and Sorry-Free Declaration Preference, Kernel Reduction versus Face-Value Comparison, Definitional-Equality Deduplication, Unsuccessful Attempt Preservation, Global Command Side-Effect Risk, Non-Declaration Command Hoisting, merge (+10 more)

### Community 8 - "Lemma Extraction"
Cohesion: 0.12
Nodes (17): Heuristic Context Minimization Risk, Mathlib extract_goal Tactic, Inaccessible Variable Reconstruction Limit, include_have_body Option, include_whole_context Option, Extracted Proof Body Robustness Risk, reconstruct_callsite Option, have2lemma (+9 more)

### Community 9 - "Proof Repair and Simplification"
Cohesion: 0.13
Nodes (15): apply_terminal_tactics Repair, enable_autoImplicit Repair, Localized Best-Effort Repair Limitation, Kernel-Safe Replacement for Native Execution, repair_proofs, relax_defeq_transparency Repair, remove_extraneous_tactics Repair, remove_unknown_options Repair (+7 more)

### Community 11 - "Declaration Extraction Flow"
Cohesion: 0.22
Nodes (10): AxleClient.check Invocation, AxleClient.extract_theorems Invocation, Extracted Document Validation Flow, Cached Default Header Rationale, Selective Elaboration Speed Tradeoff, Self-Contained Declaration Documents, extract_decls, Broader Declaration Coverage Rationale (+2 more)

### Community 12 - "Axiom Brand Lockup"
Cohesion: 0.6
Nodes (5): Axiom Brand Logo Lockup, Axiom Wordmark, Axioms as the Foundation of Reasoning, Layered Dark-to-Light Geometric Mark, The Starting Point for Reasoning

### Community 13 - "Release and Deployment Drift"
Cohesion: 0.5
Nodes (4): Keep a Changelog and Semantic Versioning, Published Changelog Mirror, Weekly Public Deployment Schedule, AXLE Release Highlights

### Community 14 - "Base Error Type"
Cohesion: 0.67
Nodes (3): Exception, AxleError, The root of all evil (in this codebase, anyway).

### Community 15 - "Runtime Error Classification"
Cohesion: 1.0
Nodes (3): AxleClient.run_one, run_one Error Mapping Tests, Typed Lean Runtime Errors

### Community 16 - "Environment Version Selection"
Cohesion: 1.0
Nodes (3): AxleClient.get_latest_environment, Basic Lean Semantic-Version Selection Policy, Latest Environment Selection Tests

### Community 17 - "Comment Removal Tests"
Cohesion: 0.67
Nodes (3): Lean Comment Removal Edge Cases, remove_comments, remove_comments Test Suite

### Community 18 - "Message Position Parsing"
Cohesion: 0.67
Nodes (3): inline_lean_messages, inline_lean_messages Test Suite, Lean Message Position Formats

### Community 19 - "Axiom Favicon"
Cohesion: 1.0
Nodes (3): Axiom Brand Favicon, Browser-Tab Brand Identity, Layered Geometric Axiom Mark

### Community 20 - "API Key Authentication"
Cohesion: 1.0
Nodes (2): API Keys for Active Request Rate Limiting, API Key Authentication

### Community 23 - "Test Package Documentation"
Cohesion: 1.0
Nodes (1): AXLE Test Package

### Community 24 - "Favicon Dark Base"
Cohesion: 1.0
Nodes (1): Dark Trapezoidal Base

### Community 25 - "Favicon Middle Facet"
Cohesion: 1.0
Nodes (1): Medium-Blue Middle Facet

### Community 26 - "Favicon Upper Facet"
Cohesion: 1.0
Nodes (1): Pale-Blue Upper Facet

## Knowledge Gaps
- **131 isolated node(s):** `Pytest configuration and fixtures for AXLE tests.`, `Mock response for verify_proof endpoint.`, `Tests for AXLE helper functions.`, `Nested block comments should be handled correctly.`, `Comment-like syntax inside strings should not be removed.` (+126 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `API Key Authentication`** (2 nodes): `API Keys for Active Request Rate Limiting`, `API Key Authentication`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Test Package Documentation`** (1 nodes): `AXLE Test Package`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Favicon Dark Base`** (1 nodes): `Dark Trapezoidal Base`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Favicon Middle Facet`** (1 nodes): `Medium-Blue Middle Facet`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Favicon Upper Facet`** (1 nodes): `Pale-Blue Upper Facet`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `AxleClient` connect `Async Client Methods` to `SDK Types and Errors`, `Endpoint Metadata and CLI`?**
  _High betweenness centrality (0.305) - this node is a cross-community bridge._
- **Why does `Document` connect `Tool Semantics and CLI` to `SDK Types and Errors`?**
  _High betweenness centrality (0.218) - this node is a cross-community bridge._
- **Why does `AXLE - Python client for the Axiom Lean Engine API.` connect `SDK Types and Errors` to `Tool Semantics and CLI`, `Async Client Methods`?**
  _High betweenness centrality (0.191) - this node is a cross-community bridge._
- **Are the 35 inferred relationships involving `AxleClient` (e.g. with `Tests for the AXLE client response types.` and `AxleBrowserLoginRequiredError`) actually correct?**
  _`AxleClient` has 35 INFERRED edges - model-reasoned connections that need verification._
- **Are the 31 inferred relationships involving `AxleIsUnavailable` (e.g. with `AxleClient` and `AXLE client for the Lean verification API.`) actually correct?**
  _`AxleIsUnavailable` has 31 INFERRED edges - model-reasoned connections that need verification._
- **Are the 31 inferred relationships involving `AxleInternalError` (e.g. with `AxleClient` and `AXLE client for the Lean verification API.`) actually correct?**
  _`AxleInternalError` has 31 INFERRED edges - model-reasoned connections that need verification._
- **Are the 30 inferred relationships involving `AxleInvalidArgument` (e.g. with `AxleClient` and `AXLE client for the Lean verification API.`) actually correct?**
  _`AxleInvalidArgument` has 30 INFERRED edges - model-reasoned connections that need verification._