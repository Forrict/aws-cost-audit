"""Check 10: CloudWatch log groups without retention policy."""

import boto3

from aws_cost_optimizer.models import CheckResult, Finding, Status


def run() -> CheckResult:
    logs = boto3.client("logs")

    log_groups: list[dict] = []
    paginator = logs.get_paginator("describe_log_groups")
    try:
        for page in paginator.paginate():
            log_groups.extend(page.get("logGroups", []))
    except Exception as e:
        return CheckResult(
            check_name="CloudWatch Log Retention",
            status=Status.INFO,
            finding=f"Could not retrieve log groups: {e}",
            recommendation="Ensure IAM permissions include logs:DescribeLogGroups.",
        )

    if not log_groups:
        return CheckResult(
            check_name="CloudWatch Log Retention",
            status=Status.PASS,
            finding="No CloudWatch log groups found.",
            recommendation="No action required.",
        )

    no_retention = [lg for lg in log_groups if "retentionInDays" not in lg]

    if not no_retention:
        return CheckResult(
            check_name="CloudWatch Log Retention",
            status=Status.PASS,
            finding=f"All {len(log_groups)} log group(s) have a retention policy.",
            recommendation="No action required.",
        )

    findings = [Finding(lg["logGroupName"], "no retention policy (logs kept forever)") for lg in no_retention]
    names = ", ".join(f.resource_id for f in findings[:5])
    suffix = f" (and {len(findings) - 5} more)" if len(findings) > 5 else ""

    return CheckResult(
        check_name="CloudWatch Log Retention",
        status=Status.WARN,
        finding=f"{len(no_retention)} of {len(log_groups)} log group(s) have no retention policy: {names}{suffix}",
        recommendation="Set a retention policy (e.g. 30–90 days) on all log groups to avoid unbounded storage costs.",
        findings=findings,
    )
