# Shared Zero-Hit Delete Allowlist

## Wave 0 Executed Deletes

These files were deleted because they satisfied the Wave 0 criteria:
- no live runtime import hits
- not exported by a live package init chain
- not used by dynamic import/loading paths
- not required by active tests
- not required by active SOP/runtime contracts

Deleted:
- `shared/config_cloud_ref/__init__.py`
- `shared/config_cloud_ref/_base.py`
- `shared/config_cloud_ref/agent_a.py`
- `shared/config_cloud_ref/agent_b.py`
- `shared/config_cloud_ref/agent_g.py`
- `shared/config_cloud_ref/api_credentials.py`
- `shared/config_cloud_ref/flow_engine.py`
- `shared/config_cloud_ref/market_structure.py`
- `shared/config_cloud_ref/persistence.py`
- `shared/config_cloud_ref/server.py`
- `shared/config_cloud_ref/websocket.py`
- `shared/models/active_option.py`

## Rationale

`shared/config_cloud_ref` had no remaining live runtime, test, SOP, or active OpenSpec consumers after the active spec reference moved to `shared/config/agent_g.py`, so the package entrypoint became deletable as well. `shared/models/active_option.py` had no live imports, no package export, and no dynamic loader references.
