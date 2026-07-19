# Graph Report - AxiomMath/axle-mcp-server@64842f5  (2026-07-18)

## Corpus Check
- 11 files · ~80,139 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 162 nodes · 259 edges · 9 communities detected
- Extraction: 72% EXTRACTED · 28% INFERRED · 0% AMBIGUOUS · INFERRED: 72 edges (avg confidence: 0.82)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Dispatcher Contract Tests|Dispatcher Contract Tests]]
- [[_COMMUNITY_Server Runtime Plumbing|Server Runtime Plumbing]]
- [[_COMMUNITY_Live Upstream Contract|Live Upstream Contract]]
- [[_COMMUNITY_Environment Selection|Environment Selection]]
- [[_COMMUNITY_Transport and File Authority|Transport and File Authority]]
- [[_COMMUNITY_Tool Schema Assembly|Tool Schema Assembly]]
- [[_COMMUNITY_MCP Authoring Demo|MCP Authoring Demo]]
- [[_COMMUNITY_Field Schema Tests|Field Schema Tests]]
- [[_COMMUNITY_Authentication Headers|Authentication Headers]]

## God Nodes (most connected - your core abstractions)
1. `handle_call_tool()` - 31 edges
2. `field_to_json_schema()` - 12 edges
3. `_default_environment()` - 9 edges
4. `_resolve_default_environment()` - 8 edges
5. `_build_tool_defs()` - 7 edges
6. `Authorized File URI to Content Resolution` - 7 edges
7. `Default Lean Environment Selection Policy` - 7 edges
8. `Import-Time Upstream Contract Snapshot` - 7 edges
9. `MCP Tool Call Dispatcher` - 7 edges
10. `Stateless Streamable HTTP MCP Transport` - 7 edges

## Surprising Connections (you probably didn't know these)
- `AXLE MCP Server` --references--> `Live-Metadata-Derived MCP Tool Surface`  [INFERRED]
  README.md → axle_mcp_server/server.py
- `Local AXLE API Key Configuration` --shares_data_with--> `Upstream Authentication and Attribution Header Policy`  [INFERRED]
  README.md → axle_mcp_server/server.py
- `Hosted MCP Bearer Connector` --shares_data_with--> `Per-Request Credential and Client-IP Context`  [INFERRED]
  README.md → axle_mcp_server/server.py
- `Stateless Streamable HTTP MCP Transport` --implements--> `Hosted MCP Bearer Connector`  [INFERRED]
  axle_mcp_server/server.py → README.md
- `Local AXLE API Key Configuration` --conceptually_related_to--> `MCP Stdio Transport`  [INFERRED]
  README.md → axle_mcp_server/server.py

## Hyperedges (group relationships)
- **Credential Propagation Across Transports** — readme_local_api_key_configuration, readme_hosted_bearer_connector, server_request_context_credentials, server_upstream_header_policy, server_upstream_endpoint_client [INFERRED 0.90]
- **Restart-Bound Live Tool Contract Pipeline** — server_upstream_endpoint_client, server_import_time_contract_snapshot, server_default_environment_policy, server_runtime_input_schema, server_dynamic_tool_surface, server_mcp_tool_dispatcher [INFERRED 0.90]
- **File URI Authority and Transport Flow** — server_file_uri_schema_adapter, server_canonical_file_path, server_mcp_root_authority, server_file_uri_resolution, server_stdio_transport, server_streamable_http_transport [EXTRACTED 1.00]
- **MCP-assisted Lean split-and-sorry flow** — demo_split_and_sorry_request, demo_proof_lean, demo_claude_read_operation, demo_axle_theorem2sorry_mcp, demo_theorem_to_sorry_transform, demo_claude_write_operations, demo_div6_imp_div2_and_div3_lean, demo_sq_even_iff_lean, demo_sq_even_dvd_prod_lean [EXTRACTED 1.00]
- **Three generated Lean output files** — demo_div6_imp_div2_and_div3_lean, demo_sq_even_iff_lean, demo_sq_even_dvd_prod_lean [EXTRACTED 1.00]

## Communities

### Community 0 - "Dispatcher Contract Tests"
Cohesion: 0.13
Nodes (25): handle_call_tool(), test_accepts_file_inside_declared_roots(), test_empty_roots_list_denies_all(), test_file_uri_accepts_bare_absolute_path(), test_file_uri_substitutes_into_content(), test_http_mode_rejects_file_uri(), test_rejects_both_content_and_file_uri(), test_rejects_directory() (+17 more)

### Community 1 - "Server Runtime Plumbing"
Cohesion: 0.09
Nodes (25): _build_http_app(), _call_endpoint(), _client_roots(), _Config, _extract_request_id(), _get_shared_link(), _http_main(), InputField (+17 more)

### Community 2 - "Live Upstream Contract"
Cohesion: 0.11
Nodes (26): Patched Test Startup Contract, Post-Import Network-Isolation Timing Gap, Fixture and Production Static-Tool Exclusion Drift, AXLE MCP Server, Default Lean Environment Selection Policy, Live-Metadata-Derived MCP Tool Surface, Explicit Null Environment Bypasses Runtime Default, AXLE Field to JSON Schema Translation (+18 more)

### Community 3 - "Environment Selection"
Cohesion: 0.22
Nodes (14): _default_environment(), Select the latest lean-4.{minor}.{micro} environment by version., Pick the default environment, honoring `AXLE_DEFAULT_ENVIRONMENT`.      If the e, _resolve_default_environment(), test_falls_back_to_last_when_no_match(), test_ignores_non_lean_prefix(), test_ignores_rc_versions(), test_micro_version_tiebreaker() (+6 more)

### Community 4 - "Transport and File Authority"
Cohesion: 0.21
Nodes (15): Hosted MCP Bearer Connector, Local AXLE API Key Configuration, Canonical File Path Resolution, Authorized File URI to Content Resolution, ASGI Authorization and Client-IP Extraction, Tri-State MCP Root Authority, Direct MCP Route Redirect-Avoidance Rationale, Per-Request Credential and Client-IP Context (+7 more)

### Community 5 - "Tool Schema Assembly"
Cohesion: 0.16
Nodes (12): _patch_startup_data(), Patch module-level state so tests don't hit the network., build_input_schema(), _build_tool_defs(), _has_textarea_content(), _inject_file_uri(), Add `file_uri` as an optional alternative to `content`.      The "exactly one of, test_environment_gets_default() (+4 more)

### Community 6 - "MCP Authoring Demo"
Cohesion: 0.29
Nodes (13): Axle theorem2sorry MCP Tool, Claude Code Session (Opus 4.6), Claude Code Read Operation, Claude Code Write Operations, div6_imp_div2_and_div3.lean, Mathlib, proof.lean, Separated MCP Content Transformation and Host File I/O (+5 more)

### Community 7 - "Field Schema Tests"
Cohesion: 0.3
Nodes (11): field_to_json_schema(), test_checkbox(), test_description_and_default(), test_dict(), test_list_int(), test_list_string(), test_number(), test_text() (+3 more)

### Community 8 - "Authentication Headers"
Cohesion: 0.24
Nodes (10): _extract_request_context(), _fetch_json(), _headers(), Pull Authorization + first X-Forwarded-For hop from an ASGI scope., GET a JSON resource from the AXLE API (sync, used at startup)., test_extract_request_context_falls_back_to_client(), test_extract_request_context_reads_headers_and_client(), test_headers_no_auth_configured() (+2 more)

## Knowledge Gaps
- **26 isolated node(s):** `Patch module-level state so tests don't hit the network.`, `_Config`, `MCP Server for AXLE (https://axle.axiommath.ai/).  Copyright (c) 2026 Axiom Math`, `GET a JSON resource from the AXLE API (sync, used at startup).`, `POST to an AXLE endpoint and return the parsed JSON response.` (+21 more)
  These have ≤1 connection - possible missing edges or undocumented components.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `handle_call_tool()` connect `Dispatcher Contract Tests` to `Server Runtime Plumbing`?**
  _High betweenness centrality (0.180) - this node is a cross-community bridge._
- **Why does `field_to_json_schema()` connect `Field Schema Tests` to `Server Runtime Plumbing`, `Tool Schema Assembly`?**
  _High betweenness centrality (0.083) - this node is a cross-community bridge._
- **Why does `_default_environment()` connect `Environment Selection` to `Server Runtime Plumbing`, `Tool Schema Assembly`?**
  _High betweenness centrality (0.058) - this node is a cross-community bridge._
- **Are the 24 inferred relationships involving `handle_call_tool()` (e.g. with `test_file_uri_substitutes_into_content()` and `test_file_uri_accepts_bare_absolute_path()`) actually correct?**
  _`handle_call_tool()` has 24 INFERRED edges - model-reasoned connections that need verification._
- **Are the 10 inferred relationships involving `field_to_json_schema()` (e.g. with `test_text()` and `test_textarea()`) actually correct?**
  _`field_to_json_schema()` has 10 INFERRED edges - model-reasoned connections that need verification._
- **Are the 6 inferred relationships involving `_default_environment()` (e.g. with `_patch_startup_data()` and `test_selects_latest_stable_version()`) actually correct?**
  _`_default_environment()` has 6 INFERRED edges - model-reasoned connections that need verification._
- **Are the 5 inferred relationships involving `_resolve_default_environment()` (e.g. with `test_resolve_falls_back_to_auto_pick_when_unset()` and `test_resolve_uses_override_when_set_to_known_env()`) actually correct?**
  _`_resolve_default_environment()` has 5 INFERRED edges - model-reasoned connections that need verification._