# Session Archives

## Purpose
- Preserve one immutable context bundle per substantive change set.
- Prevent context overwrite across multi-agent handoffs.

## Directory Convention
- `notes/sessions/YYYY-MM-DD/<task-id>/`
- Recommended `<task-id>`: `HHMM_<scope>_<hotfix|mod|feature>`

## Required Files Per Session
- `project_state.md`
- `open_tasks.md`
- `handoff.md`
- `meta.yaml`

## Bootstrap
1. Copy templates from `notes/sessions/_templates/`.
2. Fill `meta.yaml` first (`branch`, `base_commit`, `parent_session`).
3. Update `notes/context/*.md` pointers to the new active session.

