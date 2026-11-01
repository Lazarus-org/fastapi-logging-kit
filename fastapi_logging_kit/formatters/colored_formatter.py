"""Concurrent-safe colored console output without mutating shared formatters."""

import re
from logging import Formatter, LogRecord
from typing import Any, Literal, Mapping

from fastapi_logging_kit.utils.console_colorizer import colorize_log_format

_ANSI = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")


class ColoredFormatter(Formatter):
    def __init__(
        self,
        fmt: str | None = None,
        datefmt: str | None = None,
        style: Literal["%", "{", "$"] = "%",
        validate: bool = True,
        *,
        defaults: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(
            fmt, datefmt, style=style, validate=validate, defaults=defaults
        )
        self._original_fmt = self._style._fmt
        self._formatter_style = style
        self._colored: dict[str, Formatter] = {}

    def format(self, record: LogRecord) -> str:
        if self._formatter_style != "%" or _ANSI.search(self._original_fmt):
            return super().format(record)
        formatter = self._colored.get(record.levelname)
        if formatter is None:
            fmt = colorize_log_format(self._original_fmt, record.levelname)
            formatter = Formatter(fmt, self.datefmt)
            self._colored[record.levelname] = formatter
        return formatter.format(record)
