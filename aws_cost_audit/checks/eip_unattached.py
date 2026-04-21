"""Check 5: Unattached Elastic IPs."""

import boto3

from aws_cost_audit.models import CheckResult, Finding, Status


def run() -> CheckResult:
    ec2 = boto3.client("ec2")

    try:
        response = ec2.describe_addresses()
    except Exception as e:
        return CheckResult(
            check_name="Unattached Elastic IPs",
            status=Status.INFO,
            finding=f"Could not retrieve Elastic IPs: {e}",
            recommendation="Ensure IAM permissions include ec2:DescribeAddresses.",
        )

    addresses = response.get("Addresses", [])
    unattached = [a for a in addresses if not a.get("AssociationId")]

    if not unattached:
        return CheckResult(
            check_name="Unattached Elastic IPs",
            status=Status.PASS,
            finding="No unattached Elastic IPs found.",
            recommendation="No action required.",
        )

    findings = [
        Finding(a.get("PublicIp", "unknown"), "not associated with any instance or NAT gateway")
        for a in unattached
    ]
    ips = ", ".join(f.resource_id for f in findings)

    return CheckResult(
        check_name="Unattached Elastic IPs",
        status=Status.FAIL,
        finding=f"{len(unattached)} unattached Elastic IP(s): {ips}",
        recommendation="Release unattached EIPs to avoid idle charges (~$3.60/month per IP).",
        findings=findings,
    )
