"""Global configuration via pydantic-settings."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseSettings):
    """Application-wide configuration with defaults and env overrides."""

    model_config = SettingsConfigDict(
        env_prefix="GEN_CERBOT_",
        env_file=".env",
        env_file_encoding="utf-8",
    )

    config_dir: Path = Path.home() / ".config" / "gen_cerbot"
    data_dir: Path = Path.home() / ".local" / "share" / "gen_cerbot"
    log_file: Path = Path.home() / ".local" / "share" / "gen_cerbot" / "gen_cerbot.log"
    registry_file: Path = Path.home() / ".config" / "gen_cerbot" / "registry.json"
    config_toml: Path = Path.home() / ".config" / "gen_cerbot" / "config.toml"
    default_lang: str = "en"
    dry_run: bool = False
    staging: bool = False
    verbose: bool = False

    def ensure_dirs(self) -> None:
        """Create configuration and data directories if they don't exist."""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)
