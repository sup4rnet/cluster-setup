"""Safe YAML editing with ruamel.yaml that preserves comments and formatting."""

import shutil
from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from ruamel.yaml import YAML

from .config import BACKUP_DIR


def get_yaml() -> YAML:
    """Get configured YAML instance."""
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.default_flow_style = False
    yaml.indent(mapping=4, sequence=4, offset=2)
    return yaml


def load_yaml(path: Path) -> Any:
    """Load a YAML file preserving comments."""
    yaml = get_yaml()
    with open(path, "r") as f:
        return yaml.load(f)


def save_yaml(path: Path, data: Any, backup: bool = True) -> None:
    """Save YAML file atomically with optional backup.

    Args:
        path: File path to save to
        data: YAML data to save
        backup: Whether to create a backup before overwriting
    """
    if backup and path.exists():
        create_backup(path)

    # Write to temp file first, then rename (atomic)
    with NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as tmp:
        yaml = get_yaml()
        yaml.dump(data, tmp)
        tmp_path = Path(tmp.name)

    # Atomic rename
    shutil.move(tmp_path, path)


def create_backup(path: Path) -> Path:
    """Create a backup of a file.

    Args:
        path: File to backup

    Returns:
        Path to the backup file
    """
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"{path.stem}_{timestamp}{path.suffix}"
    backup_path = BACKUP_DIR / backup_name

    shutil.copy2(path, backup_path)
    return backup_path


def append_to_list(data: Any, key: str, value: str) -> bool:
    """Append a value to a list in the YAML data.

    Args:
        data: YAML data structure
        key: Key of the list to append to
        value: Value to append

    Returns:
        True if successful, False if key not found or not a list
    """
    if key not in data:
        return False

    if not isinstance(data[key], list):
        return False

    if value not in data[key]:
        data[key].append(value)

    return True


def remove_from_list(data: Any, key: str, value: str) -> bool:
    """Remove a value from a list in the YAML data.

    Args:
        data: YAML data structure
        key: Key of the list to remove from
        value: Value to remove

    Returns:
        True if value was removed, False otherwise
    """
    if key not in data:
        return False

    if not isinstance(data[key], list):
        return False

    if value in data[key]:
        data[key].remove(value)
        return True

    return False
