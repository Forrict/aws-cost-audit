"""Shared data models for check results."""

from dataclasses import dataclass, field
from enum import Enum


class Status(str, Enum):
    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"
    INFO = "INFO"


@dataclass
class Finding:
    resource_id: str
    detail: str

    def to_dict(self) -> dict:
        return {"resource_id": self.resource_id, "detail": self.detail}


@dataclass
class CheckResult:
    check_name: str
    status: Status
    finding: str
    recommendation: str
    findings: list[Finding] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "check_name": self.check_name,
            "status": self.status.value,
            "finding": self.finding,
            "recommendation": self.recommendation,
            "findings": [f.to_dict() for f in self.findings],
        }
