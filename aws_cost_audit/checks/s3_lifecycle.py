"""Check 8: S3 buckets without lifecycle policies."""

import boto3
from botocore.exceptions import ClientError

from aws_cost_audit.models import CheckResult, Finding, Status


def run() -> CheckResult:
    s3 = boto3.client("s3")

    try:
        response = s3.list_buckets()
    except Exception as e:
        return CheckResult(
            check_name="S3 Lifecycle Policies",
            status=Status.INFO,
            finding=f"Could not list S3 buckets: {e}",
            recommendation="Ensure IAM permissions include s3:ListAllMyBuckets.",
        )

    buckets = response.get("Buckets", [])
    if not buckets:
        return CheckResult(
            check_name="S3 Lifecycle Policies",
            status=Status.PASS,
            finding="No S3 buckets found.",
            recommendation="No action required.",
        )

    no_lifecycle: list[Finding] = []
    for bucket in buckets:
        name = bucket["Name"]
        try:
            s3.get_bucket_lifecycle_configuration(Bucket=name)
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchLifecycleConfiguration":
                no_lifecycle.append(Finding(name, "no lifecycle policy"))
            # Other errors (access denied, etc.) — skip silently

    if not no_lifecycle:
        return CheckResult(
            check_name="S3 Lifecycle Policies",
            status=Status.PASS,
            finding=f"All {len(buckets)} bucket(s) have a lifecycle policy configured.",
            recommendation="No action required.",
        )

    names = ", ".join(f.resource_id for f in no_lifecycle)
    return CheckResult(
        check_name="S3 Lifecycle Policies",
        status=Status.WARN,
        finding=f"{len(no_lifecycle)} of {len(buckets)} bucket(s) lack a lifecycle policy: {names}",
        recommendation=(
            "Add lifecycle rules to transition objects to"
            " cheaper storage tiers (S3-IA, Glacier) and"
            " expire old objects."
        ),
        findings=no_lifecycle,
    )
