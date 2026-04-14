"""Check 12: Previous-generation EC2 instance types still in use."""

import boto3

from aws_cost_optimizer.models import CheckResult, Finding, Status

# Common previous-gen prefixes (t1, m1, m2, m3, c1, c3, r3, i2, hs1, g2, cr1, cc1, cc2)
PREVIOUS_GEN_PREFIXES = (
    "t1.",
    "m1.",
    "m2.",
    "m3.",
    "c1.",
    "c3.",
    "r3.",
    "i2.",
    "hs1.",
    "g2.",
    "cr1.",
    "cc1.",
    "cc2.",
    "cg1.",
)


def run() -> CheckResult:
    ec2 = boto3.client("ec2")

    try:
        response = ec2.describe_instances(
            Filters=[{"Name": "instance-state-name", "Values": ["running", "stopped"]}]
        )
    except Exception as e:
        return CheckResult(
            check_name="Previous-Generation Instance Types",
            status=Status.INFO,
            finding=f"Could not retrieve EC2 instances: {e}",
            recommendation="Ensure IAM permissions include ec2:DescribeInstances.",
        )

    old_gen: list[Finding] = []
    for reservation in response.get("Reservations", []):
        for instance in reservation.get("Instances", []):
            itype = instance["InstanceType"]
            if any(itype.startswith(p) for p in PREVIOUS_GEN_PREFIXES):
                old_gen.append(
                    Finding(
                        instance["InstanceId"], f"type: {itype}, state: {instance['State']['Name']}"
                    )
                )

    if not old_gen:
        return CheckResult(
            check_name="Previous-Generation Instance Types",
            status=Status.PASS,
            finding="No previous-generation instance types found.",
            recommendation="No action required.",
        )

    ids = ", ".join(f.resource_id for f in old_gen)
    return CheckResult(
        check_name="Previous-Generation Instance Types",
        status=Status.WARN,
        finding=f"{len(old_gen)} instance(s) running on previous-gen types: {ids}",
        recommendation=(
            "Migrate to current-generation equivalents"
            " (e.g. m3\u2192m6i, c3\u2192c6i) for better performance"
            " at lower cost (typically 20\u201340% cheaper)."
        ),
        findings=old_gen,
    )
