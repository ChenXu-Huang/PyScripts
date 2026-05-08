import json
from pathlib import Path
from typing import Any, Optional

from .logger import get_logger, log_exceptions
from . import ROOT_DIR
logger = get_logger(__name__)


class JsonConfigStore:
    """Generic JSON-backed config store with nested key-path access."""

    def __init__(self, config_dir: str | Path = ".") -> None:
        self.config_dir = Path(config_dir)

    @log_exceptions()
    def _load_json(self, file_path: Path, default: dict[str, Any] | None = None) -> dict[str, Any]:
        if file_path.exists():
            try:
                with file_path.open("r", encoding="utf-8") as f:
                    return json.load(f)
            except json.JSONDecodeError as e:
                logger.error("Failed to parse %s: %s", file_path.name, e)
        if default is not None:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with file_path.open("w", encoding="utf-8", newline="") as f:
                json.dump(default, f, indent=4, ensure_ascii=False)
            return dict(default)
        return {}

    @log_exceptions()
    def _save_json(self, data: dict[str, Any], file_path: Path) -> None:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with file_path.open("w", encoding="utf-8", newline="") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    @staticmethod
    def _get_nested(data: dict, path: str, default: Any = None) -> Any:
        keys = path.split(".")
        val = data
        for key in keys:
            if isinstance(val, dict) and key in val:
                val = val[key]
            else:
                return default
        return val

    @staticmethod
    def _set_nested(data: dict, path: str, value: Any) -> None:
        keys = path.split(".")
        for key in keys[:-1]:
            data = data.setdefault(key, {})
        data[keys[-1]] = value


class ConfigManager(JsonConfigStore):
    _DEFAULT_APP = {
        "language": "zh_CN",
        "theme": "system",
        "regex_replacer": {"ignore_case": False, "backup": False},
        "table_grapher": {"mode": "smooth", "plot_together": True},
        "data_generator": {"distribution": "normal"},
    }

    def __init__(self, config_dir: str | Path = ".") -> None:
        super().__init__(config_dir)
        self.app_file = self.config_dir / "app.json"
        self.history_file = self.config_dir / "history.json"

        self.app: dict[str, Any] = {}
        self.history: dict[str, Any] = {}

        self.reload()
        logger.info("Configuration loaded successfully from %s", self.config_dir.resolve())

    def reload(self) -> None:
        self.app = self._load_json(self.app_file, self._DEFAULT_APP)
        self.history = self._load_json(self.history_file)

    def save_all(self) -> None:
        self.save_app()
        self.save_history()

    def save_app(self) -> None:
        self._save_json(self.app, self.app_file)

    def save_history(self) -> None:
        self._save_json(self.history, self.history_file)

    def get_app(self, key_path: str, default: Any = None) -> Any:
        return self._get_nested(self.app, key_path, default)

    def set_app(self, key_path: str, value: Any) -> None:
        self._set_nested(self.app, key_path, value)

    def get_history(self, key_path: str, default: Any = None) -> Any:
        return self._get_nested(self.history, key_path, default)

    def append_history(self, key_path: str, value: Any, max_len: Optional[int] = 20) -> None:
        target_list = self.get_history(key_path, [])
        if not isinstance(target_list, list):
            target_list = []

        if value in target_list:
            target_list.remove(value)

        target_list.insert(0, value)

        if max_len is not None:
            target_list = target_list[:max_len]

        self._set_nested(self.history, key_path, target_list)


config_manager = ConfigManager(config_dir=ROOT_DIR / "config")
