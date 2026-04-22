## ADDED Requirements

### Requirement: Pure Active Options Shims Must Be Removed
The repository SHALL not retain `shared/services/active_options_engines.py` or
`shared/services/active_options_input.py` once consumers have been retargeted to
`shared_rust.services`.

#### Scenario: Shim Files Still Present
- **WHEN** the runtime source tree still contains either pure shim file after consumer retarget
- **THEN** the refactor is incomplete and the shim files MUST be deleted.

### Requirement: Consumer Imports Must Target the Neutral Rust Surface
The following consumers SHALL import directly from `shared_rust.services`:
`l2_decision/signals/flow/deg_composer.py`,
`l2_decision/signals/flow/flow_engine_d.py`,
`l2_decision/signals/flow/flow_engine_e.py`,
`l2_decision/signals/flow/flow_engine_g.py`,
and `app/loops/compute_loop.py`.

#### Scenario: Consumer Still Imports the Shim
- **WHEN** any of the above consumers imports from `shared.services.active_options_engines`
  or `shared.services.active_options_input`
- **THEN** the import retarget has not been completed.

### Requirement: No Residual Runtime References to Retired Shim Modules
Runtime source files SHALL not retain references to the retired shim module names after the cutover.

#### Scenario: Residual Runtime Reference Found
- **WHEN** `rg "active_options_engines|active_options_input" app l0_ingest l1_compute l2_decision l3_assembly l4_ui shared scripts --include="*.py"`
  returns any runtime source match
- **THEN** the cutover MUST be blocked until the reference is removed.
