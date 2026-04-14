"""Check 3: Old EBS snapshots (> 90 days)."""

from datetime import datetime, timedelta, timezone

import boto3

from aws_cost_optimizer.models import CheckResult, Finding, Status

MAX_AGE_DAYS = 90


def run() -> CheckResult:
    ec2 = boto3.client("ec2")

    try:
        sts = boto3.client("sts")
        account_id = sts.get_caller_identity()["Account"]
        response = ec2.describe_snapshots(OwnerIds=[account_id])
    except Exception as e:
        return CheckResult(
            check_name="Old EBS Snapshots",
            status=Status.INFO,
            finding=f"Could not retrieve snapshots: {e}",
            recommendation="Ensure IAM permissions include ec2:DescribeSnapshots and sts:GetCallerIdentity.",
        )

    cutoff = datetime.now(tz=timezone.utc) - timedelta(days=MAX_AGE_DAYS)
    old_snaps = [
        s for s in response.get("Snapshots", [])
        if s["StartTime"] < cutoff
    ]

    if not old_snaps:
        return CheckResult(
            check_name="Old EBS Snapshots",
            status=Status.PASS,
            finding=f"No EBS snapshots older than {MAX_AGE_DAYS} days found.",
            recommendation="No action required.",
        )

    findings = [
        Finding(s["SnapshotId"], f"{s['VolumeSize']} GiB, created {s['StartTime'].date()}")
        for s in old_snaps
    ]
    ids = ", ".join(f.resource_id for f in findings)
    total_gib = sum(s["VolumeSize"] for s in old_snaps)

    return CheckResult(
        check_name="Old EBS Snapshots",
        status=Status.WARN,
        finding=f"{len(old_snaps)} snapshot(s) older than {MAX_AGE_DAYS} days ({total_gib} GiB total): {ids}",
        recommendation="Review and delete snapshots that are no longer needed. Implement a lifecycle policy using AWS Data Lifecycle Manager.",
        findings=findings,
    )
