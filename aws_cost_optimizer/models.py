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


@dataclass
class CheckResult:
    check_name: str
    status: Status
    finding: str
    recommendation: str
    findings: list[Finding] = field(default_factory=list)
