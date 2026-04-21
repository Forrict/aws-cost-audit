"""Check 13: Unused Lambda functions (no invocations in > 30 days)."""

from datetime import datetime, timedelta, timezone

import boto3

from aws_cost_audit.models import CheckResult, Finding, Status

IDLE_DAYS = 30


def run() -> CheckResult:
    lmb = boto3.client("lambda")
    cw = boto3.client("cloudwatch")

    functions: list[dict] = []
    paginator = lmb.get_paginator("list_functions")
    try:
        for page in paginator.paginate():
            functions.extend(page.get("Functions", []))  # type: ignore[arg-type]
    except Exception as e:
        return CheckResult(
            check_name="Unused Lambda Functions",
            status=Status.INFO,
            finding=f"Could not list Lambda functions: {e}",
            recommendation="Ensure IAM permissions include lambda:ListFunctions.",
        )

    if not functions:
        return CheckResult(
            check_name="Unused Lambda Functions",
            status=Status.PASS,
            finding="No Lambda functions found.",
            recommendation="No action required.",
        )

    end_time = datetime.now(tz=timezone.utc)
    start_time = end_time - timedelta(days=IDLE_DAYS)
    unused: list[Finding] = []

    for fn in functions:
        fn_name = fn["FunctionName"]
        try:
            metrics = cw.get_metric_statistics(
                Namespace="AWS/Lambda",
                MetricName="Invocations",
                Dimensions=[{"Name": "FunctionName", "Value": fn_name}],
                StartTime=start_time,
                EndTime=end_time,
                Period=IDLE_DAYS * 86400,
                Statistics=["Sum"],
            )
            datapoints = metrics.get("Datapoints", [])
            total = sum(d["Sum"] for d in datapoints) if datapoints else 0
            if total == 0:
                unused.append(Finding(fn_name, f"0 invocations in last {IDLE_DAYS} days"))
        except Exception:
            pass

    if not unused:
        return CheckResult(
            check_name="Unused Lambda Functions",
            status=Status.PASS,
            finding=f"All {len(functions)} Lambda function(s) have recent invocations.",
            recommendation="No action required.",
        )

    names = ", ".join(f.resource_id for f in unused[:5])
    suffix = f" (and {len(unused) - 5} more)" if len(unused) > 5 else ""
    return CheckResult(
        check_name="Unused Lambda Functions",
        status=Status.WARN,
        finding=(
            f"{len(unused)} Lambda function(s) with no invocations"
            f" in {IDLE_DAYS} days: {names}{suffix}"
        ),
        recommendation=(
            "Delete unused Lambda functions and their associated"
            " resources (CloudWatch log groups, IAM roles,"
            " layers)."
        ),
        findings=unused,
    )
