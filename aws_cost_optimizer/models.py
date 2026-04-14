"""Shared data models for check results."""

from dataclasses import dataclass, field
from enum import Enum
from typing import List


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
    findings: List[Finding] = field(default_factory=list)
