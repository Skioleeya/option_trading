"""WallMigration submodule — UI mappings.

Maps Call/Put type to CSS color tokens.
Imports from this submodule's own palette — not from global theme.
"""

from app.ui.wall_migration import palette

CALL_ROW = {
    "type_label": palette.CALL_TYPE_LABEL,
    "type_bg":    palette.CALL_TYPE_BG,
    "type_text":  palette.CALL_TYPE_TEXT,
    "dot_color":  palette.CALL_DOT_COLOR,
}

PUT_ROW = {
    "type_label": palette.PUT_TYPE_LABEL,
    "type_bg":    palette.PUT_TYPE_BG,
    "type_text":  palette.PUT_TYPE_TEXT,
    "dot_color":  palette.PUT_DOT_COLOR,
}
