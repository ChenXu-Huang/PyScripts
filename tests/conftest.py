from src.logger import LoggerManager, LoggerConfig

LoggerManager.configure(
    LoggerConfig(
        name="tests",
        log_dir="logs",
        level="DEBUG",
        console=False,
        json_file=False,
        text_file=True,
        error_file=True,
        max_bytes=10 * 1024 * 1024,
        backup_count=5,
        ignored_loggers=["matplotlib"]
    )
)
