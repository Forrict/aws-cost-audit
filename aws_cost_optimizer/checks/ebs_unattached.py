"""Check 2: Unattached EBS volumes."""

import boto3

from aws_cost_optimizer.models import CheckResult, Finding, Status


def run() -> CheckResult:
    ec2 = boto3.client("ec2")

    try:
        response = ec2.describe_volumes(Filters=[{"Name": "status", "Values": ["available"]}])
    except Exception as e:
        return CheckResult(
            check_name="Unattached EBS Volumes",
            status=Status.INFO,
            finding=f"Could not retrieve EBS volumes: {e}",
            recommendation="Ensure IAM permissions include ec2:DescribeVolumes.",
        )

    volumes = response.get("Volumes", [])
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
