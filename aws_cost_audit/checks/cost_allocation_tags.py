"""Check 15: Missing cost allocation tags on key resources."""

import boto3
from botocore.exceptions import ClientError

from aws_cost_audit.models import CheckResult, Finding, Status

# Common cost allocation tag keys to check for
REQUIRED_TAG_KEYS = ["Environment", "Project", "Owner", "CostCenter"]
MIN_TAGS_REQUIRED = 1  # At least one of the above should be present


def _tags_to_dict(tags: list) -> dict:
    return {t["Key"]: t["Value"] for t in (tags or [])}


def _has_cost_tags(tags: list) -> bool:
    tag_dict = _tags_to_dict(tags)
    return any(k in tag_dict for k in REQUIRED_TAG_KEYS)


def run() -> CheckResult:
    ec2 = boto3.client("ec2")
    rds = boto3.client("rds")

    untagged: list[Finding] = []
    total = 0

    # EC2 instances
    try:
        response = ec2.describe_instances(
            Filters=[{"Name": "instance-state-name", "Values": ["running", "stopped"]}]
        )
        for reservation in response.get("Reservations", []):
            for instance in reservation.get("Instances", []):
                total += 1
                if not _has_cost_tags(instance.get("Tags", [])):
                    untagged.append(
                        Finding(instance["InstanceId"], "EC2 instance missing cost allocation tags")
                    )
    except Exception:
        pass

    # RDS instances
    try:
        rds_response = rds.describe_db_instances()
        for db in rds_response.get("DBInstances", []):
            total += 1
            if not _has_cost_tags(db.get("TagList", [])):
                untagged.append(
                    Finding(db["DBInstanceIdentifier"], "RDS instance missing cost allocation tags")
                )
    except Exception:
        pass

    # S3 buckets (sample — tag API differs)
    s3 = boto3.client("s3")
    try:
        buckets = s3.list_buckets().get("Buckets", [])
        for bucket in buckets:
            total += 1
            try:
                tagging = s3.get_bucket_tagging(Bucket=bucket["Name"])
                tags = tagging.get("TagSet", [])
            except ClientError as e:
                if e.response["Error"]["Code"] == "NoSuchTagSet":
                    tags = []
                else:
                    continue
            if not _has_cost_tags(tags):
                untagged.append(Finding(bucket["Name"], "S3 bucket missing cost allocation tags"))
    except Exception:
        pass

    if total == 0:
        return CheckResult(
            check_name="Cost Allocation Tags",
            status=Status.INFO,
            finding="No EC2, RDS, or S3 resources found to evaluate.",
            recommendation=(
                "Ensure IAM permissions include"
                " ec2:DescribeInstances, rds:DescribeDBInstances,"
                " s3:ListAllMyBuckets, s3:GetBucketTagging."
            ),
        )

    if not untagged:
        return CheckResult(
            check_name="Cost Allocation Tags",
            status=Status.PASS,
            finding=(
                f"All {total} sampled resource(s) have at least one"
                f" cost allocation tag ({', '.join(REQUIRED_TAG_KEYS)})."
            ),
            recommendation="No action required.",
        )

    pct = len(untagged) / total * 100
    sample = ", ".join(f.resource_id for f in untagged[:5])
    suffix = f" (and {len(untagged) - 5} more)" if len(untagged) > 5 else ""
    return CheckResult(
        check_name="Cost Allocation Tags",
        status=Status.WARN,
        finding=(
            f"{len(untagged)} of {total} resource(s) ({pct:.0f}%)"
            f" lack cost tags ({', '.join(REQUIRED_TAG_KEYS)}):"
            f" {sample}{suffix}"
        ),
        recommendation=(
            "Apply consistent cost allocation tags to all"
            " resources. Enable Cost Allocation Tags in Billing"
            " Console to track spending by tag."
        ),
        findings=untagged,
    )
