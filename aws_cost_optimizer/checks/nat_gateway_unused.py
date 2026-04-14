"""Check 9: Unused NAT Gateways."""

from datetime import datetime, timedelta, timezone

import boto3

from aws_cost_optimizer.models import CheckResult, Finding, Status


def run() -> CheckResult:
    ec2 = boto3.client("ec2")
    cw = boto3.client("cloudwatch")

    try:
        response = ec2.describe_nat_gateways(Filters=[{"Name": "state", "Values": ["available"]}])
    except Exception as e:
        return CheckResult(
            check_name="Unused NAT Gateways",
            status=Status.INFO,
            finding=f"Could not retrieve NAT Gateways: {e}",
            recommendation="Ensure IAM permissions include ec2:DescribeNatGateways.",
        )

    gateways = response.get("NatGateways", [])
    if not gateways:
        return CheckResult(
            check_name="Unused NAT Gateways",
            status=Status.PASS,
            finding="No active NAT Gateways found.",
            recommendation="No action required.",
        )

    end_time = datetime.now(tz=timezone.utc)
    start_time = end_time - timedelta(days=7)
    idle: list[Finding] = []

    for gw in gateways:
        gw_id = gw["NatGatewayId"]
        try:
            metrics = cw.get_metric_statistics(
                Namespace="AWS/NATGateway",
                MetricName="BytesOutToDestination",
                Dimensions=[{"Name": "NatGatewayId", "Value": gw_id}],
                StartTime=start_time,
                EndTime=end_time,
                Period=604800,
                Statistics=["Sum"],
            )
            datapoints = metrics.get("Datapoints", [])
            total_bytes = sum(d["Sum"] for d in datapoints) if datapoints else 0
            if total_bytes == 0:
                idle.append(Finding(gw_id, "zero bytes sent in last 7 days"))
        except Exception:
            pass

    if not idle:
        return CheckResult(
            check_name="Unused NAT Gateways",
            status=Status.PASS,
            finding=f"All {len(gateways)} NAT Gateway(s) show traffic.",
            recommendation="No action required.",
        )

    ids = ", ".join(f.resource_id for f in idle)
    return CheckResult(
        check_name="Unused NAT Gateways",
        status=Status.WARN,
        finding=f"{len(idle)} idle NAT Gateway(s): {ids}",
        recommendation=(
            "Delete unused NAT Gateways to save ~$32/month per gateway plus data transfer charges."
        ),
        findings=idle,
    )
