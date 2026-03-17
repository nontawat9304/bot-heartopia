"""
macro_validator.py - Validates route_macro.json schema before playback.
"""
from src.logger import get_logger

logger = get_logger()

VALID_ACTIONS = {"walk", "rotate", "interact", "wait"}
VALID_WALK_KEYS = {"w", "a", "s", "d"}

_SCHEMA = {
    "walk":     {"required": [], "optional": {"key": str, "duration": (int, float),
                                               "until": str, "tag": str}},
    "rotate":   {"required": [], "optional": {"dx": (int, float), "dy": (int, float),
                                               "tag": str}},
    "interact": {"required": [], "optional": {"tag": str}},
    "wait":     {"required": [], "optional": {"min": (int, float), "max": (int, float),
                                               "tag": str}},
}


def validate(actions, path="root") -> list[str]:
    """
    Recursively validate action list.
    Returns list of error strings (empty = valid).
    """
    errors = []

    for i, action in enumerate(actions):
        loc = f"{path}[{i}]"

        if not isinstance(action, dict):
            errors.append(f"{loc}: expected dict, got {type(action).__name__}")
            continue

        # ── loop block ──────────────────────────────────────────────────
        if "loop" in action:
            loop_val = action["loop"]
            if not isinstance(loop_val, int):
                errors.append(f"{loc}.loop: must be int, got {type(loop_val).__name__}")
            sub = action.get("actions")
            if sub is None:
                errors.append(f"{loc}: loop block missing 'actions' list")
            elif not isinstance(sub, list):
                errors.append(f"{loc}.actions: must be list")
            else:
                errors.extend(validate(sub, path=f"{loc}.actions"))
            continue

        # ── regular action ───────────────────────────────────────────────
        action_type = action.get("action")
        if action_type is None:
            errors.append(f"{loc}: missing 'action' field")
            continue
        if action_type not in VALID_ACTIONS:
            errors.append(f"{loc}: unknown action '{action_type}' "
                          f"(valid: {sorted(VALID_ACTIONS)})")
            continue

        schema = _SCHEMA[action_type]

        # Check required fields
        for field in schema["required"]:
            if field not in action:
                errors.append(f"{loc}: '{action_type}' missing required field '{field}'")

        # Check optional field types
        for field, expected_type in schema["optional"].items():
            if field in action:
                val = action[field]
                if not isinstance(val, expected_type):
                    errors.append(
                        f"{loc}.{field}: expected {expected_type}, got {type(val).__name__}"
                    )

        # Extra checks
        if action_type == "walk":
            key = action.get("key", "w")
            if key not in VALID_WALK_KEYS:
                errors.append(f"{loc}.key: invalid walk key '{key}' "
                              f"(valid: {sorted(VALID_WALK_KEYS)})")
            dur = action.get("duration", 1.0)
            if isinstance(dur, (int, float)) and dur <= 0:
                errors.append(f"{loc}.duration: must be > 0, got {dur}")

        if action_type == "wait":
            mn = action.get("min", 0.5)
            mx = action.get("max", 1.5)
            if isinstance(mn, (int, float)) and isinstance(mx, (int, float)) and mn > mx:
                errors.append(f"{loc}: wait min ({mn}) > max ({mx})")

    return errors


def validate_and_log(actions) -> bool:
    """Returns True if valid, False if errors found (errors logged as warnings)."""
    errors = validate(actions)
    if errors:
        logger.warning(f"Macro validation failed ({len(errors)} error(s)):")
        for e in errors:
            logger.warning(f"  ✗ {e}")
        return False
    logger.info("Macro validation passed.")
    return True
