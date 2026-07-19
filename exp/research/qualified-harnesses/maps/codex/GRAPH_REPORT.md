# Graph Report - /Users/engineer/ws/codex (focused 71-file core and enforcement scope)  (2026-07-15)

## Corpus Check
- 71 files · ~141,778 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 2330 nodes · 5940 edges · 30 communities detected
- Extraction: 72% EXTRACTED · 28% INFERRED · 0% AMBIGUOUS · INFERRED: 1641 edges (avg confidence: 0.8)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Session and Turn Lifecycle|Session and Turn Lifecycle]]
- [[_COMMUNITY_Filesystem Sandbox Policy|Filesystem Sandbox Policy]]
- [[_COMMUNITY_CLI Command Routing|CLI Command Routing]]
- [[_COMMUNITY_Unified Exec Process Manager|Unified Exec Process Manager]]
- [[_COMMUNITY_Tool Registry and Routing|Tool Registry and Routing]]
- [[_COMMUNITY_Thread and Subagent Manager|Thread and Subagent Manager]]
- [[_COMMUNITY_Execution Sandbox Manager|Execution Sandbox Manager]]
- [[_COMMUNITY_Tool Specs and Remote Filesystem|Tool Specs and Remote Filesystem]]
- [[_COMMUNITY_Model Client Transport|Model Client Transport]]
- [[_COMMUNITY_Approval and Tool Sandboxing|Approval and Tool Sandboxing]]
- [[_COMMUNITY_Linux Sandbox Launcher|Linux Sandbox Launcher]]
- [[_COMMUNITY_Command Execution Policy|Command Execution Policy]]
- [[_COMMUNITY_App Server Session Permissions|App Server Session Permissions]]
- [[_COMMUNITY_Model Metadata and Instructions|Model Metadata and Instructions]]
- [[_COMMUNITY_Provider Catalog and Auth|Provider Catalog and Auth]]
- [[_COMMUNITY_Apply Patch Engine|Apply Patch Engine]]
- [[_COMMUNITY_Patch and Shell Handlers|Patch and Shell Handlers]]
- [[_COMMUNITY_Headless Exec Client|Headless Exec Client]]
- [[_COMMUNITY_Stream Events and AGENTS|Stream Events and AGENTS]]
- [[_COMMUNITY_World State Diffs|World State Diffs]]
- [[_COMMUNITY_Linux Proxy Routing|Linux Proxy Routing]]
- [[_COMMUNITY_Remote Filesystem Sandbox|Remote Filesystem Sandbox]]
- [[_COMMUNITY_Auto Compaction Window|Auto Compaction Window]]
- [[_COMMUNITY_Context Token Estimation|Context Token Estimation]]
- [[_COMMUNITY_Linux Landlock Seccomp|Linux Landlock Seccomp]]
- [[_COMMUNITY_Rollout Reconstruction|Rollout Reconstruction]]
- [[_COMMUNITY_Sandbox Error Conversion|Sandbox Error Conversion]]
- [[_COMMUNITY_Filesystem Path Types|Filesystem Path Types]]
- [[_COMMUNITY_Filesystem Entry Types|Filesystem Entry Types]]
- [[_COMMUNITY_Managed Permissions Types|Managed Permissions Types]]

## God Nodes (most connected - your core abstractions)
1. `Session` - 151 edges
2. `create_filesystem_args()` - 45 edges
3. `TurnRequestProcessor` - 44 edges
4. `ThreadManager` - 40 edges
5. `FileSystemSandboxPolicy` - 39 edges
6. `cli_main()` - 37 edges
7. `try_run_sampling_request()` - 35 edges
8. `run_compact_task_inner_impl()` - 32 edges
9. `path_to_string()` - 30 edges
10. `ContextManager` - 28 edges

## Surprising Connections (you probably didn't know these)
- `built_tools()` --calls--> `extension_tool_executors()`  [INFERRED]
  /Users/engineer/ws/codex/codex-rs/core/src/session/turn.rs → /Users/engineer/ws/codex/codex-rs/core/src/tools/router.rs
- `execute_exec_request_with_after_spawn()` --calls--> `execute_exec_request()`  [INFERRED]
  /Users/engineer/ws/codex/codex-rs/core/src/sandboxing/mod.rs → /Users/engineer/ws/codex/codex-rs/core/src/exec.rs
- `exec_bwrap()` --calls--> `exec()`  [INFERRED]
  /Users/engineer/ws/codex/codex-rs/linux-sandbox/src/launcher.rs → /Users/engineer/ws/codex/codex-rs/core/src/exec.rs
- `run_main()` --calls--> `check_execpolicy_for_warnings()`  [INFERRED]
  /Users/engineer/ws/codex/codex-rs/exec/src/lib.rs → /Users/engineer/ws/codex/codex-rs/core/src/exec_policy.rs
- `append_interrupted_boundary()` --calls--> `interrupted_turn_history_marker()`  [INFERRED]
  /Users/engineer/ws/codex/codex-rs/core/src/thread_manager.rs → /Users/engineer/ws/codex/codex-rs/core/src/tasks/mod.rs

## Communities

### Community 0 - "Session and Turn Lifecycle"
Cohesion: 0.01
Nodes (137): build_compacted_history(), build_compacted_history_with_limit(), build_compaction_initial_context(), collect_user_messages(), CompactedUserMessage, compaction_status_from_result(), CompactionAnalyticsAttempt, CompactionAnalyticsDetails (+129 more)

### Community 1 - "Filesystem Sandbox Policy"
Cohesion: 0.02
Nodes (190): append_empty_directory_args(), append_empty_file_bind_data_args(), append_existing_empty_directory_args(), append_existing_empty_file_bind_data_args(), append_existing_unreadable_path_args(), append_metadata_path_masks_for_writable_root(), append_missing_empty_file_bind_data_args(), append_missing_read_only_subpath_args() (+182 more)

### Community 2 - "CLI Command Routing"
Cohesion: 0.02
Nodes (156): app_server_analytics_default_disabled_without_flag(), app_server_analytics_default_enabled_with_flag(), app_server_capability_token_flags_parse(), app_server_from_args(), app_server_listen_off_parses(), app_server_listen_stdio_url_parses(), app_server_listen_unix_socket_path_parses(), app_server_listen_unix_socket_url_parses() (+148 more)

### Community 3 - "Unified Exec Process Manager"
Cohesion: 0.04
Nodes (44): HeadTailBuffer, clamp_yield_time(), ExecCommandRequest, format_output_omission_marker(), generate_chunk_id(), ProcessEntry, ProcessStore, set_deterministic_process_ids_for_tests() (+36 more)

### Community 4 - "Tool Registry and Routing"
Cohesion: 0.03
Nodes (33): emit_unified_exec_tty_metric(), ExecCommandHandler, ExecCommandHandlerOptions, BlockingFinishContributor, cancellation_after_handler_finishes_preserves_completed_lifecycle(), cancellation_before_dispatch_admission_logs_dispatch_only_timing(), cancellation_waiting_for_runtime_cleanup_emits_only_aborted_lifecycle(), CancellationCleanupHandler (+25 more)

### Community 5 - "Thread and Subagent Manager"
Cohesion: 0.04
Nodes (30): InterruptedTurnHistoryMarker, new_submission_id(), resolve_multi_agent_version(), SessionIo, AppServerClientMetadata, Session, SessionSettingsUpdate, warm_plugins_and_skills_for_session_init() (+22 more)

### Community 6 - "Execution Sandbox Manager"
Cohesion: 0.03
Nodes (67): find_system_bwrap_in_path(), find_system_bwrap_in_search_paths(), is_user_namespace_failure(), is_wsl1(), proc_version_indicates_wsl1(), should_warn_about_system_bwrap(), system_bwrap_has_user_namespace_access(), system_bwrap_warning() (+59 more)

### Community 7 - "Tool Specs and Remote Filesystem"
Cohesion: 0.04
Nodes (72): ContextualUserFragment, FragmentRegistration, FragmentRegistrationProxy, matches_marked_text(), CopyOptions, CreateDirectoryOptions, ExecFileSystemPath, ExecFileSystemSandboxEntry (+64 more)

### Community 8 - "Model Client Transport"
Cohesion: 0.05
Nodes (32): add_originator_header(), add_responses_lite_header(), ApiTelemetry, AuthRequestTelemetryContext, build_responses_headers(), Prompt, ResponseStream, strip_image_details() (+24 more)

### Community 9 - "Approval and Tool Sandboxing"
Cohesion: 0.04
Nodes (38): ApplyPatchApprovalKey, ApplyPatchRequest, ApplyPatchRuntime, ApplyPatchRuntimeOutput, ApprovalAction, ApprovalResolution, ApprovalResolutionSource, ApprovalReviewer (+30 more)

### Community 10 - "Linux Sandbox Launcher"
Cohesion: 0.05
Nodes (70): BubblewrapLauncher, exec_bwrap(), exec_system_bwrap(), ignores_system_bwrap_when_system_bwrap_lacks_perms(), preferred_bwrap_launcher(), preferred_bwrap_supports_argv0(), system_bwrap_capabilities(), system_bwrap_launcher_for_path() (+62 more)

### Community 11 - "Command Execution Policy"
Cohesion: 0.06
Nodes (33): Decision, check_execpolicy_for_warnings(), collect_policy_files(), commands_for_exec_policy(), default_policy_path(), derive_forbidden_reason(), derive_prompt_reason(), derive_requested_execpolicy_amendment_from_prefix_rule() (+25 more)

### Community 12 - "App Server Session Permissions"
Cohesion: 0.07
Nodes (8): SessionConfiguration, map_additional_context(), ThreadSettingsBuildParams, TurnRequestProcessor, validate_response_item_image_urls(), validate_user_input_image_urls(), xcode_26_4_mcp_elicitations_auto_deny(), track_turn_resolved_config_analytics()

### Community 13 - "Model Metadata and Instructions"
Cohesion: 0.04
Nodes (43): WireApi, ApplyPatchToolType, ApprovalMessages, AutoReviewMessages, ClientVersion, ConfigShellToolType, default_input_modalities(), deserialize_optional_model_selector() (+35 more)

### Community 14 - "Provider Catalog and Auth"
Cohesion: 0.07
Nodes (34): built_in_model_providers(), create_oss_provider(), create_oss_provider_with_base_url(), merge_configured_model_providers(), ModelProviderAwsAuthInfo, ModelProviderInfo, run_debug_models_command(), amazon_bedrock_provider_creates_static_models_manager() (+26 more)

### Community 15 - "Apply Patch Engine"
Cohesion: 0.09
Nodes (45): AffectedPaths, AppliedPatch, AppliedPatchChange, AppliedPatchDelta, AppliedPatchFileChange, apply_hunks(), apply_hunks_to_files(), apply_patch() (+37 more)

### Community 16 - "Patch and Shell Handlers"
Cohesion: 0.07
Nodes (33): apply_patch_payload_command(), ApplyPatchArgumentDiffConsumer, ApplyPatchHandler, convert_apply_patch_hunks_to_protocol(), effective_patch_permissions(), file_paths_for_action(), format_update_chunks_for_progress(), hunk_source_path() (+25 more)

### Community 17 - "Headless Exec Client"
Cohesion: 0.07
Nodes (49): handle_unauthorized(), exec_policy_message_for_display(), all_thread_source_kinds(), build_exec_config(), build_review_request(), canceled_mcp_server_elicitation_response(), cwds_match(), decode_prompt_bytes() (+41 more)

### Community 18 - "Stream Events and AGENTS"
Cohesion: 0.06
Nodes (32): agents_md_paths(), candidate_filenames(), InstructionEntry, InstructionProvenance, load_project_instructions(), LoadedAgentsMd, AgentsMdCache, AgentsMdManager (+24 more)

### Community 19 - "World State Diffs"
Cohesion: 0.05
Nodes (17): AgentsMdSnapshot, AgentsMdState, FragmentRegistrationProxy<T>, apply_merge_patch_value(), create_merge_patch(), ErasedWorldStateSection, ExtensionWorldStateSection, has_legacy_fragment() (+9 more)

### Community 20 - "Linux Proxy Routing"
Cohesion: 0.08
Nodes (40): activate_proxy_routes_in_netns(), attribution_token_is_extracted_before_proxy_route_planning(), bind_local_loopback_listener(), cleanup_proxy_socket_dir(), cleanup_proxy_socket_dir_removes_bridge_artifacts(), cleanup_stale_proxy_socket_dirs_in(), cleanup_stale_proxy_socket_dirs_removes_dead_pid_directories(), close_fd() (+32 more)

### Community 21 - "Remote Filesystem Sandbox"
Cohesion: 0.09
Nodes (31): add_helper_runtime_permissions(), bazel_bwrap_env_key_is_allowed(), FileSystemSandboxRunner, helper_env(), helper_env_carries_only_allowlisted_runtime_vars(), helper_env_from_vars(), helper_env_key_is_allowed(), helper_env_preserves_corefoundation_text_encoding() (+23 more)

### Community 22 - "Auto Compaction Window"
Cohesion: 0.15
Nodes (5): AutoCompactWindow, AutoCompactWindowIds, AutoCompactWindowPrefill, AutoCompactWindowSnapshot, tracks_prefill_and_window_boundaries()

### Community 23 - "Context Token Estimation"
Cohesion: 0.26
Nodes (10): encrypted_function_output_estimate_adjustment(), estimate_encrypted_function_output_length(), estimate_item_token_count(), estimate_original_image_bytes(), estimate_reasoning_length(), estimate_response_item_model_visible_bytes(), image_data_url_estimate_adjustment(), parse_base64_image_data_url() (+2 more)

### Community 24 - "Linux Landlock Seccomp"
Cohesion: 0.21
Nodes (7): apply_permission_profile_to_current_thread(), install_filesystem_landlock_rules_on_current_thread(), install_network_seccomp_filter_on_current_thread(), network_seccomp_mode(), NetworkSeccompMode, set_no_new_privs(), should_install_network_seccomp()

### Community 25 - "Rollout Reconstruction"
Cohesion: 0.25
Nodes (8): ActiveReplaySegment, finalize_active_segment(), parse_uuid_v7(), reconstructed_window_from_session_context_window(), ReconstructedWindow, RolloutReconstruction, turn_ids_are_compatible(), TurnReferenceContextItem

### Community 27 - "Sandbox Error Conversion"
Cohesion: 1.0
Nodes (1): CodexErr

### Community 28 - "Filesystem Path Types"
Cohesion: 1.0
Nodes (1): FileSystemPath

### Community 29 - "Filesystem Entry Types"
Cohesion: 1.0
Nodes (1): FileSystemSandboxEntry

### Community 30 - "Managed Permissions Types"
Cohesion: 1.0
Nodes (1): ManagedFileSystemPermissions

## Knowledge Gaps
- **217 isolated node(s):** `InitialContextInjection`, `CompactionAnalyticsDetails`, `CompactedUserMessage`, `ExecParams`, `ExecExpirationOutcome` (+212 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Sandbox Error Conversion`** (2 nodes): `CodexErr`, `.from()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Filesystem Path Types`** (2 nodes): `FileSystemPath`, `.try_from()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Filesystem Entry Types`** (2 nodes): `FileSystemSandboxEntry`, `.try_from()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Managed Permissions Types`** (2 nodes): `ManagedFileSystemPermissions`, `.try_from()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Session` connect `Session and Turn Lifecycle` to `Unified Exec Process Manager`, `Thread and Subagent Manager`, `Approval and Tool Sandboxing`, `Patch and Shell Handlers`, `Stream Events and AGENTS`?**
  _High betweenness centrality (0.084) - this node is a cross-community bridge._
- **Why does `run_exec_session()` connect `Headless Exec Client` to `Session and Turn Lifecycle`, `Unified Exec Process Manager`, `App Server Session Permissions`, `Execution Sandbox Manager`?**
  _High betweenness centrality (0.027) - this node is a cross-community bridge._
- **Why does `walk_via_directory_reads()` connect `Tool Specs and Remote Filesystem` to `Filesystem Sandbox Policy`, `Command Execution Policy`, `App Server Session Permissions`?**
  _High betweenness centrality (0.026) - this node is a cross-community bridge._
- **Are the 10 inferred relationships involving `create_filesystem_args()` (e.g. with `.get_unreadable_globs_with_cwd()` and `.get_writable_roots_with_cwd()`) actually correct?**
  _`create_filesystem_args()` has 10 INFERRED edges - model-reasoned connections that need verification._
- **What connects `InitialContextInjection`, `CompactionAnalyticsDetails`, `CompactedUserMessage` to the rest of the system?**
  _217 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Session and Turn Lifecycle` be split into smaller, more focused modules?**
  _Cohesion score 0.01 - nodes in this community are weakly interconnected._
- **Should `Filesystem Sandbox Policy` be split into smaller, more focused modules?**
  _Cohesion score 0.02 - nodes in this community are weakly interconnected._