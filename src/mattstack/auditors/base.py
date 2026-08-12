"""Base classes and data models for the audit system."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path


class Severity(StrEnum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class AuditType(StrEnum):
    TYPES = "types"
    QUALITY = "quality"
    ENDPOINTS = "endpoints"
    TESTS = "tests"
    DEPENDENCIES = "dependencies"
    VULNERABILITIES = "vulnerabilities"


@dataclass
class AuditFinding:
    category: AuditType
    severity: Severity
    file: Path
    line: int
    message: str
    suggestion: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "category": self.category.value,
            "severity": self.severity.value,
            "file": str(self.file),
            "line": self.line,
            "message": self.message,
            "suggestion": self.suggestion,
        }


@dataclass
class AuditConfig:
    project_path: Path
    audit_types: list[AuditType] | None = None  # None = all
    live: bool = False
    write_todo: bool = True
    json_output: bool = False
    fix: bool = False
    base_url: str = "http://localhost:8000"
    min_severity: Severity | None = None  # None = show all

    @property
    def run_all(self) -> bool:
        return self.audit_types is None

    def should_run(self, audit_type: AuditType) -> bool:
        return self.run_all or audit_type in (self.audit_types or [])


class BaseAuditor(ABC):
    """Base class for all auditors."""

    audit_type: AuditType

    def __init__(self, config: AuditConfig) -> None:
        self.config = config
        self.findings: list[AuditFinding] = []

    @abstractmethod
    def run(self) -> list[AuditFinding]: ...

    def _rel(self, path: Path) -> Path:
        """Convert absolute path to relative path from project root."""
        try:
            return path.relative_to(self.config.project_path)
        except ValueError:
            return path

    def add_finding(
        self,
        severity: Severity,
        file: Path,
        line: int,
        message: str,
        suggestion: str = "",
    ) -> None:
        self.findings.append(
            AuditFinding(
                category=self.audit_type,
                severity=severity,
                file=file,
                line=line,
                message=message,
                suggestion=suggestion,
            )
        )

    @property
    def error_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.ERROR)

    @property
    def warning_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.WARNING)

    @property
    def summary(self) -> str:
        return (
            f"{self.audit_type.value}: "
            f"{self.error_count} errors, {self.warning_count} warnings, "
            f"{len(self.findings) - self.error_count - self.warning_count} info"
        )


@dataclass
class AuditReport:
    """Collected results from all auditors."""

    findings: list[AuditFinding] = field(default_factory=list)
    auditors_run: list[str] = field(default_factory=list)

    @property
    def error_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.ERROR)

    @property
    def warning_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.WARNING)

    @property
    def info_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.INFO)

    def to_dict(self) -> dict[str, object]:
        return {
            "auditors_run": self.auditors_run,
            "summary": {
                "errors": self.error_count,
                "warnings": self.warning_count,
                "info": self.info_count,
                "total": len(self.findings),
            },
            "findings": [f.to_dict() for f in self.findings],
        }
