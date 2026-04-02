## ADDED Requirements

### Requirement: services_root Transitional Artifact Must Be Retired
The repository SHALL not keep `shared_rust/services_root.pyd` once all runtime consumers have moved to `shared_rust.services`.

#### Scenario: Transitional Artifact Still Present
- **WHEN** the runtime tree has no consumer importing `shared_rust.services_root`
- **THEN** `shared_rust/services_root.pyd` MUST be removed.

### Requirement: services Namespace Continuity Must Hold
Deleting `services_root.pyd` SHALL NOT break `shared_rust.services` imports used by runtime code.

#### Scenario: Post-Deletion Service Import Smoke
- **WHEN** `from shared_rust.services import build_columnar_payload, RollingRealizedVolatility` is executed
- **THEN** the import MUST succeed.

### Requirement: No Replacement Shim Allowed
This retirement SHALL NOT introduce any new shim file or alias namespace for `services_root`.

#### Scenario: Retirement Completion Review
- **WHEN** this change is reviewed
- **THEN** there MUST be no new `services_root` compatibility shim in `shared/` or `shared_rust/`.
