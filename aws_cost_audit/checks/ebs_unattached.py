"""Check 2: Unattached EBS volumes."""

import boto3

from aws_cost_audit.models import CheckResult, Finding, Status


def run() -> CheckResult:
    ec2 = boto3.client("ec2")

    try:
        volumes: list[dict] = []
        paginator = ec2.get_paginator("describe_volumes")
        for page in paginator.paginate(
            Filters=[{"Name": "status", "Values": ["available"]}]
        ):
            volumes.extend(page.get("Volumes", []))  # type: ignore[arg-type]
    except Exception as e:
        return CheckResult(
            check_name="Unattached EBS Volumes",
            status=Status.INFO,
            finding=f"Could not retrieve EBS volumes: {e}",
            recommendation="Ensure IAM permissions include ec2:DescribeVolumes.",
        )
    if not volumes:
        return CheckResult(
            check_name="Unattached EBS Volumes",
            status=Status.PASS,
            finding="No unattached EBS volumes found.",
            recommendation="No action required.",
        )

    findings = [
        Finding(v["VolumeId"], f"{v['Size']} GiB {v['VolumeType']} in {v['AvailabilityZone']}")
        for v in volumes
    ]
    ids = ", ".join(f.resource_id for f in findings)
    total_gib = sum(v["Size"] for v in volumes)

    return CheckResult(
        check_name="Unattached EBS Volumes",
        status=Status.FAIL,
        finding=f"{len(volumes)} unattached volume(s) totalling {total_gib} GiB: {ids}",
        recommendation=(
            "Delete volumes that are no longer needed or create snapshots before deletion."
        ),
        findings=findings,
    )
