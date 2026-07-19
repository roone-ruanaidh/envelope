# Graph Report - /Users/engineer/ws/grok-build (focused 71-file core and enforcement scope; one file skipped by sensitive-file detection)  (2026-07-15)

## Corpus Check
- 70 files · ~355,729 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 4508 nodes · 12482 edges · 47 communities detected
- Extraction: 74% EXTRACTED · 26% INFERRED · 0% AMBIGUOUS · INFERRED: 3263 edges (avg confidence: 0.8)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Model Configuration Resolution|Model Configuration Resolution]]
- [[_COMMUNITY_Session Turn and Tools|Session Turn and Tools]]
- [[_COMMUNITY_Canonical Conversation IR|Canonical Conversation IR]]
- [[_COMMUNITY_JSONL Persistence and Config|JSONL Persistence and Config]]
- [[_COMMUNITY_Bash Tool Runtime|Bash Tool Runtime]]
- [[_COMMUNITY_Shell Permissions and Parsing|Shell Permissions and Parsing]]
- [[_COMMUNITY_Tool Registry and Bridge|Tool Registry and Bridge]]
- [[_COMMUNITY_Permission Manager and Overrides|Permission Manager and Overrides]]
- [[_COMMUNITY_CLI and Task Spawning|CLI and Task Spawning]]
- [[_COMMUNITY_Compacted History Assembly|Compacted History Assembly]]
- [[_COMMUNITY_Local and Remote Workspace|Local and Remote Workspace]]
- [[_COMMUNITY_Agent Definition Presets|Agent Definition Presets]]
- [[_COMMUNITY_Terminal Process Runtime|Terminal Process Runtime]]
- [[_COMMUNITY_Sampling Client Transport|Sampling Client Transport]]
- [[_COMMUNITY_Sampling Request Types|Sampling Request Types]]
- [[_COMMUNITY_Kernel Sandbox Profiles|Kernel Sandbox Profiles]]
- [[_COMMUNITY_Agent Builder|Agent Builder]]
- [[_COMMUNITY_Prompt Context Rendering|Prompt Context Rendering]]
- [[_COMMUNITY_Subagent Lifecycle|Subagent Lifecycle]]
- [[_COMMUNITY_Chat State Request Budgeting|Chat State Request Budgeting]]
- [[_COMMUNITY_Sampler Retry Actor|Sampler Retry Actor]]
- [[_COMMUNITY_Patch and Filesystem Tools|Patch and Filesystem Tools]]
- [[_COMMUNITY_Pre Tool Hook Dispatcher|Pre Tool Hook Dispatcher]]
- [[_COMMUNITY_Computer Error Types|Computer Error Types]]
- [[_COMMUNITY_Session Spawn and Permissions|Session Spawn and Permissions]]
- [[_COMMUNITY_Cgroup Memory Monitor|Cgroup Memory Monitor]]
- [[_COMMUNITY_User Context Template|User Context Template]]
- [[_COMMUNITY_Subagent Configuration Discovery|Subagent Configuration Discovery]]
- [[_COMMUNITY_Compaction Item Contract|Compaction Item Contract]]
- [[_COMMUNITY_Compaction Threshold Policy|Compaction Threshold Policy]]
- [[_COMMUNITY_Notification Queue|Notification Queue]]
- [[_COMMUNITY_Git Change Collection|Git Change Collection]]
- [[_COMMUNITY_Git Root Resolution|Git Root Resolution]]
- [[_COMMUNITY_Git Commit Resolution|Git Commit Resolution]]
- [[_COMMUNITY_VCS Detection|VCS Detection]]
- [[_COMMUNITY_Worktree DB Rebuild|Worktree DB Rebuild]]
- [[_COMMUNITY_Worktree DB Paths|Worktree DB Paths]]
- [[_COMMUNITY_Fuzzy Close Request|Fuzzy Close Request]]
- [[_COMMUNITY_Client FS Listing|Client FS Listing]]
- [[_COMMUNITY_Client FS Stat|Client FS Stat]]
- [[_COMMUNITY_Worktree Creation|Worktree Creation]]
- [[_COMMUNITY_Worktree Apply|Worktree Apply]]
- [[_COMMUNITY_Worktree Listing|Worktree Listing]]
- [[_COMMUNITY_Worktree Inspection|Worktree Inspection]]
- [[_COMMUNITY_Worktree Garbage Collection|Worktree Garbage Collection]]
- [[_COMMUNITY_Dynamic Tool Dispatch Contract|Dynamic Tool Dispatch Contract]]
- [[_COMMUNITY_Tool Stream Terminality|Tool Stream Terminality]]

## God Nodes (most connected - your core abstractions)
1. `new()` - 82 edges
2. `JsonlStorageAdapter` - 72 edges
3. `handle_subagent_request()` - 71 edges
4. `Config` - 68 edges
5. `spawn_session_actor()` - 57 edges
6. `AgentBuilder` - 55 edges
7. `resolve_model_list()` - 53 edges
8. `ToolBridge` - 44 edges
9. `test_model_entry()` - 42 edges
10. `load()` - 39 edges

## Surprising Connections (you probably didn't know these)
- `parse_blocking_result()` --calls--> `Decision`  [INFERRED]
  /Users/engineer/ws/grok-build/crates/codegen/xai-grok-hooks/src/runner/command.rs → /Users/engineer/ws/grok-build/crates/codegen/xai-grok-workspace/src/permission/types.rs
- `run()` --calls--> `trust_bwrap_marker_for_devbox()`  [INFERRED]
  /Users/engineer/ws/grok-build/crates/codegen/xai-grok-workspace/src/bin/workspace_server.rs → /Users/engineer/ws/grok-build/crates/codegen/xai-grok-sandbox/src/lib.rs
- `run_command_hook()` --calls--> `Args`  [INFERRED]
  /Users/engineer/ws/grok-build/crates/codegen/xai-grok-hooks/src/runner/command.rs → /Users/engineer/ws/grok-build/crates/codegen/xai-grok-workspace/src/bin/workspace_server.rs
- `to_acp_model_info()` --calls--> `reasoning_effort_meta_value()`  [INFERRED]
  /Users/engineer/ws/grok-build/crates/codegen/xai-grok-shell/src/agent/config.rs → /Users/engineer/ws/grok-build/crates/codegen/xai-grok-sampling-types/src/types.rs
- `to_acp_model_info()` --calls--> `reasoning_efforts_meta_value()`  [INFERRED]
  /Users/engineer/ws/grok-build/crates/codegen/xai-grok-shell/src/agent/config.rs → /Users/engineer/ws/grok-build/crates/codegen/xai-grok-sampling-types/src/types.rs

## Communities

### Community 0 - "Model Configuration Resolution"
Cohesion: 0.01
Nodes (413): acp_model_meta_always_has_context_window(), acp_model_meta_always_includes_agent_type(), acp_model_meta_derives_first_option_when_no_default(), acp_model_meta_emits_reasoning_effort_when_supported(), acp_model_meta_emits_reasoning_efforts_and_derives_legacy(), acp_model_meta_includes_agent_type_when_present(), acp_model_meta_keeps_explicit_scalar_when_list_present(), acp_model_meta_omits_reasoning_efforts_when_list_empty() (+405 more)

### Community 1 - "Session Turn and Tools"
Cohesion: 0.01
Nodes (188): Agent, should_auto_compact_check(), resolve_shell_for_prompt(), fallback_to_exit_code_deny(), fallback_to_exit_code_failure(), fallback_to_exit_code_zero(), find_local_shell_assignments(), find_unresolved_bare_form() (+180 more)

### Community 2 - "Canonical Conversation IR"
Cohesion: 0.01
Nodes (239): build_compacted_history(), build_compacted_history_full_scenario(), build_compacted_history_minimal_no_reminder(), build_compacted_history_multi_turn_with_parallel_tool_calls(), build_compacted_history_no_user_query(), build_compacted_history_omits_agents_md_when_none(), build_compacted_history_tags_agents_md_with_project_instructions(), build_compacted_history_transcript_hint() (+231 more)

### Community 3 - "JSONL Persistence and Config"
Cohesion: 0.02
Nodes (185): AgentScope, jemalloc_allocator_stats(), add_dismissed_plugin_cta(), add_dismissed_plugin_cta_to_file(), add_hooks_path(), add_hooks_path_to_file(), apply_managed_settings_features(), apply_managed_settings_features_inner() (+177 more)

### Community 4 - "Bash Tool Runtime"
Cohesion: 0.01
Nodes (99): annotations(), background_chat_completion_is_none(), background_command_starts(), background_injects_python_unbuffered(), background_operator_allowed_by_default(), background_operator_mid_command_rejected(), background_operator_rejected(), background_operator_rejected_without_is_background_hint_when_disabled() (+91 more)

### Community 5 - "Shell Permissions and Parsing"
Cohesion: 0.02
Nodes (181): all_commands_from_script(), BashCommandHighlights, break_operator_suffixes(), env_scan(), heredoc_payload_byte_ranges(), heredoc_payload_empty_on_parse_error(), heredoc_payload_ranges_cover_body_not_opener(), is_env_assignment() (+173 more)

### Community 6 - "Tool Registry and Bridge"
Cohesion: 0.02
Nodes (107): between_turn_bash_completions_scoped_to_owning_session(), completed_task(), KindFixture, MockTerminal, register_fixture(), tool_kind_returns_registered_kind_per_namespace_and_none_for_unknown(), ToolBridge, ToolBridgeResult (+99 more)

### Community 7 - "Permission Manager and Overrides"
Cohesion: 0.03
Nodes (179): transcript_hint_needs_a_location(), AuthScheme, BearerResolver, config_without_doom_loop_recovery_deserializes_to_none(), HeaderInjector, OriginClientInfo, retry_policy_defaults(), RetryPolicy (+171 more)

### Community 8 - "CLI and Task Spawning"
Cohesion: 0.03
Nodes (158): CliAgentOverrides, PluginsConfig, resolve_subagent_permission_mode(), subagent_permission_mode_precedence(), flush(), apply_agent_endpoint_args(), apply_headless_args_to_config(), assert_prof_active() (+150 more)

### Community 9 - "Compacted History Assembly"
Cohesion: 0.02
Nodes (138): assert_clean_summary(), BackgroundTaskSummary, bound_captured_output(), bound_captured_output_keeps_head_and_tail_on_char_boundaries(), CompactedHistoryInput, CompactionAttempt, CompactionInputs, CompactionServerSummary (+130 more)

### Community 10 - "Local and Remote Workspace"
Cohesion: 0.02
Nodes (96): compaction_attempt_defaults_optional_fields_for_old_artifacts(), compaction_attempt_serde_roundtrip_and_skips_none(), laziness_detector_block_round_trips_through_serde(), laziness_detector_include_reasoning_serde_states(), mcp_server_ref_parse_and_reject(), ModelSwitchIncompatibleAgentError, historical_doom_loop_warning_deserializes_as_unknown(), unknown_synthetic_reason_deserializes_for_forward_compat() (+88 more)

### Community 11 - "Agent Definition Presets"
Cohesion: 0.02
Nodes (110): session_tools_allowed_clamp(), AgentColor, AgentDefinition, all_toolset_presets(), bash_tool_config(), BashConfig, BuiltinAgentName, carries_discipline_false_for_every_template_and_audience() (+102 more)

### Community 12 - "Terminal Process Runtime"
Cohesion: 0.04
Nodes (79): CgroupGuard, MemoryMonitor, install_child_network_filter(), has_dangling_tool_calls(), should_restrict_child_network(), SessionActor, background_child_is_reaped_via_process_scope(), BackgroundReason (+71 more)

### Community 13 - "Sampling Client Transport"
Cohesion: 0.03
Nodes (82): agent_version(), apply_terminal_event_overrides(), bearer_resolver_replaces_authorization_header(), ClientDefaults, CountingCallback, deserialize_response_event(), deserialize_response_event_ignores_context_details_on_non_terminal_events(), deserialize_response_event_overrides_total_tokens_from_context_details() (+74 more)

### Community 14 - "Sampling Request Types"
Cohesion: 0.02
Nodes (55): std::sync::Arc<T>, MockItem, select_turns_to_compact(), snap_does_not_advance_when_already_safe(), snap_to_safe_boundary(), snaps_past_tool_results(), SplitPlan, splits_at_correct_index() (+47 more)

### Community 15 - "Kernel Sandbox Profiles"
Cohesion: 0.03
Nodes (76): hosted_tool_gating(), SandboxSettingsConfig, bwrap_blocked_placeholder(), bwrap_blocked_source_for_path(), bwrap_deny_plan(), bwrap_reexec_binds_nonexistent_deny_read_paths(), bwrap_reexec_command(), bwrap_reexec_for_profile() (+68 more)

### Community 16 - "Agent Builder"
Cohesion: 0.03
Nodes (49): agent_type_restricted_to_listed_types(), AgentBuilder, ask_user_question_allowlist_builds_without_plan_tools(), bare_agent_allows_all_spawns(), build_pager_agent(), build_task_description(), build_task_description_builtin_includes_tools(), build_task_description_contains_header_and_footer() (+41 more)

### Community 17 - "Prompt Context Rendering"
Cohesion: 0.04
Nodes (68): agents_md_user_reminder_included_for_default_template(), base_template_ctx(), child_general_purpose_context(), child_prompt_context_is_complete(), child_prompt_delivers_full_agents_md(), child_prompt_excludes_persona_catalog(), child_prompt_has_no_system_prompt_override(), child_prompt_has_prompt_body() (+60 more)

### Community 18 - "Subagent Lifecycle"
Cohesion: 0.04
Nodes (70): handle_subagent_request(), task_model_override_error(), AutoCompactThresholdTiers, await_subagent_turn_or_cancellation(), BootstrapInitialContext, cancel_pending_subagent_at_promote(), cancellation_error_message(), cancelled_orphan_finish() (+62 more)

### Community 19 - "Chat State Request Budgeting"
Cohesion: 0.04
Nodes (43): HistoryRepairReport, ChatStateActor, ChatStateActor, ByteCounter, ChatStateActor, compact_images_to_byte_budget(), conversation_body_bytes(), evicted_image_uses_honest_placeholder() (+35 more)

### Community 20 - "Sampler Retry Actor"
Cohesion: 0.06
Nodes (52): apply_retry_decision(), AttemptOutcome, drive_l2(), emit_failed(), emit_retrying(), handle_cancellation(), run_request_task(), send_completion() (+44 more)

### Community 21 - "Patch and Filesystem Tools"
Cohesion: 0.08
Nodes (31): first_attempt_success_does_not_fire_retry_callbacks(), is_permission_error(), is_test_transient_write_lock_error(), is_transient_write_lock_error(), is_windows_transient_write_lock_raw_os_error(), LocalFs, non_transient_errors_are_not_retried(), persistent_transient_lock_exhausts_retry_budget() (+23 more)

### Community 22 - "Pre Tool Hook Dispatcher"
Cohesion: 0.21
Nodes (33): all_hooks_allow_results_in_allow(), allow_broad_deny_specific_non_matching_allows(), allow_broad_deny_specific_tool_match(), allow_then_deny_denies(), disabled_hook_is_skipped_allows(), dispatch_non_blocking(), dispatch_pre_tool_use(), empty_registry_allows() (+25 more)

### Community 23 - "Computer Error Types"
Cohesion: 0.12
Nodes (15): AsyncFileSystem, BackgroundHandle, Computer, ComputerError, io_error_kind_is_a_directory(), io_error_kind_preserved_through_from(), io_with_kind_matches_local_fs_dispatch_for_not_found(), io_with_kind_preserves_not_found() (+7 more)

### Community 24 - "Session Spawn and Permissions"
Cohesion: 0.11
Nodes (8): drop_cli_catchall_allows(), no_pin_keeps_everything(), pin_drops_cli_bare_and_prefix_bash_keeps_scoped(), pin_drops_cli_catchalls_keeps_scoped(), SessionInitResult, SessionRestartActions, SessionThread, spawn_session_on_thread()

### Community 25 - "Cgroup Memory Monitor"
Cohesion: 0.14
Nodes (9): CgroupHandle, CgroupMemoryConfig, Inotify, inotify_add_watch(), inotify_init1(), MemoryHighEvent, MemoryHighMonitor, parse_memory_events_high() (+1 more)

### Community 26 - "User Context Template"
Cohesion: 0.15
Nodes (9): McpServerEntry, normalize_git_status(), normalize_git_status_truncates_over_limit(), RuleEntry, template_override_deserialize_custom_map(), template_override_deserialize_strings(), template_override_round_trip(), UserMessagePlaceholders (+1 more)

### Community 27 - "Subagent Configuration Discovery"
Cohesion: 0.27
Nodes (2): RequirementSource, SubagentsConfig

### Community 28 - "Compaction Item Contract"
Cohesion: 0.33
Nodes (5): CompactionFileRef, CompactionItem, CompactionItemBuilder, CompactionItemFactory, CompactionRole

### Community 29 - "Compaction Threshold Policy"
Cohesion: 0.67
Nodes (1): CompactionPolicy

### Community 30 - "Notification Queue"
Cohesion: 1.0
Nodes (1): PendingNotification

### Community 32 - "Git Change Collection"
Cohesion: 1.0
Nodes (1): GitCollectChangesReq

### Community 33 - "Git Root Resolution"
Cohesion: 1.0
Nodes (1): GitResolveRootReq

### Community 34 - "Git Commit Resolution"
Cohesion: 1.0
Nodes (1): GitCurrentCommitReq

### Community 35 - "VCS Detection"
Cohesion: 1.0
Nodes (1): DetectVcsKindReq

### Community 36 - "Worktree DB Rebuild"
Cohesion: 1.0
Nodes (1): WorktreeDbRebuildReq

### Community 37 - "Worktree DB Paths"
Cohesion: 1.0
Nodes (1): WorktreeDbPathReq

### Community 38 - "Fuzzy Close Request"
Cohesion: 1.0
Nodes (1): FuzzyCloseReq

### Community 39 - "Client FS Listing"
Cohesion: 1.0
Nodes (1): ClientFsListReq

### Community 40 - "Client FS Stat"
Cohesion: 1.0
Nodes (1): ClientFsStatReq

### Community 41 - "Worktree Creation"
Cohesion: 1.0
Nodes (1): CreateWorktreeRequest

### Community 42 - "Worktree Apply"
Cohesion: 1.0
Nodes (1): ApplyWorktreeRequest

### Community 43 - "Worktree Listing"
Cohesion: 1.0
Nodes (1): WorktreeListReq

### Community 44 - "Worktree Inspection"
Cohesion: 1.0
Nodes (1): WorktreeShowReq

### Community 45 - "Worktree Garbage Collection"
Cohesion: 1.0
Nodes (1): WorktreeGcReq

### Community 46 - "Dynamic Tool Dispatch Contract"
Cohesion: 1.0
Nodes (1): ToolDispatch

### Community 47 - "Tool Stream Terminality"
Cohesion: 1.0
Nodes (1): ToolStreamItem<T>

## Knowledge Gaps
- **267 isolated node(s):** `PreToolUseResult`, `HookOutput`, `TraceContext`, `Box<dyn TraceContext>`, `ImageUrl` (+262 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Subagent Configuration Discovery`** (12 nodes): `RequirementSource`, `.fmt()`, `.path()`, `SubagentsConfig`, `.discover_personas()`, `.discover_personas_in_dir()`, `.discover_roles()`, `.discover_roles_in_dir()`, `.get_persona()`, `.get_role()`, `.is_subagent_enabled()`, `.resolve()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Compaction Threshold Policy`** (3 nodes): `compaction.rs`, `CompactionPolicy`, `.default()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Notification Queue`** (2 nodes): `notification_drain.rs`, `PendingNotification`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Git Change Collection`** (2 nodes): `GitCollectChangesReq`, `.execute()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Git Root Resolution`** (2 nodes): `GitResolveRootReq`, `.execute()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Git Commit Resolution`** (2 nodes): `GitCurrentCommitReq`, `.execute()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `VCS Detection`** (2 nodes): `DetectVcsKindReq`, `.execute()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Worktree DB Rebuild`** (2 nodes): `WorktreeDbRebuildReq`, `.execute()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Worktree DB Paths`** (2 nodes): `WorktreeDbPathReq`, `.execute()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Fuzzy Close Request`** (2 nodes): `FuzzyCloseReq`, `.execute()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Client FS Listing`** (2 nodes): `ClientFsListReq`, `.execute()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Client FS Stat`** (2 nodes): `ClientFsStatReq`, `.execute()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Worktree Creation`** (2 nodes): `CreateWorktreeRequest`, `.execute()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Worktree Apply`** (2 nodes): `ApplyWorktreeRequest`, `.execute()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Worktree Listing`** (2 nodes): `WorktreeListReq`, `.execute()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Worktree Inspection`** (2 nodes): `WorktreeShowReq`, `.execute()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Worktree Garbage Collection`** (2 nodes): `WorktreeGcReq`, `.execute()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Dynamic Tool Dispatch Contract`** (2 nodes): `dispatch.rs`, `ToolDispatch`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Tool Stream Terminality`** (2 nodes): `ToolStreamItem<T>`, `.is_terminal()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `spawn_session_actor()` connect `Session Turn and Tools` to `Model Configuration Resolution`, `Canonical Conversation IR`, `JSONL Persistence and Config`, `Tool Registry and Bridge`, `Permission Manager and Overrides`, `CLI and Task Spawning`, `Local and Remote Workspace`, `Terminal Process Runtime`, `Sampling Client Transport`, `Prompt Context Rendering`, `Chat State Request Budgeting`, `Sampler Retry Actor`, `Session Spawn and Permissions`?**
  _High betweenness centrality (0.048) - this node is a cross-community bridge._
- **Why does `handle_subagent_request()` connect `Subagent Lifecycle` to `Model Configuration Resolution`, `Session Turn and Tools`, `Canonical Conversation IR`, `JSONL Persistence and Config`, `Shell Permissions and Parsing`, `Permission Manager and Overrides`, `CLI and Task Spawning`, `Agent Definition Presets`, `Terminal Process Runtime`, `Sampling Client Transport`, `Chat State Request Budgeting`, `Session Spawn and Permissions`?**
  _High betweenness centrality (0.026) - this node is a cross-community bridge._
- **Why does `render_subagent_template()` connect `Prompt Context Rendering` to `Session Turn and Tools`, `Sampling Client Transport`?**
  _High betweenness centrality (0.019) - this node is a cross-community bridge._
- **Are the 7 inferred relationships involving `new()` (e.g. with `grok_home()` and `.new()`) actually correct?**
  _`new()` has 7 INFERRED edges - model-reasoned connections that need verification._
- **Are the 69 inferred relationships involving `handle_subagent_request()` (e.g. with `.clone()` and `resolve_agent_definition()`) actually correct?**
  _`handle_subagent_request()` has 69 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `Config` (e.g. with `.resolve_compaction_verbatim_input()` and `.resolve_subagent_worktree_snapshot_enabled()`) actually correct?**
  _`Config` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Are the 53 inferred relationships involving `spawn_session_actor()` (e.g. with `.deny_read_globs()` and `.is_empty()`) actually correct?**
  _`spawn_session_actor()` has 53 INFERRED edges - model-reasoned connections that need verification._