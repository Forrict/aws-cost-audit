"""Check 6: Oversized EC2 instances (right-sizing candidates via CloudWatch)."""

from datetime import datetime, timedelta, timezone

import boto3

from aws_cost_optimizer.models import CheckResult, Finding, Status

CPU_THRESHOLD = 20.0  # percent average over 14 days


def run() -> CheckResult:
    ec2 = boto3.client("ec2")
    cw = boto3.client("cloudwatch")

    try:
        response = ec2.describe_instances(
            Filters=[{"Name": "instance-state-name", "Values": ["running"]}]
        )
    except Exception as e:
        return CheckResult(
            check_name="Oversized EC2 Instances",
            status=Status.INFO,
            finding=f"Could not retrieve EC2 instances: {e}",
            recommendation="Ensure IAM permissions include ec2:DescribeInstances.",
        )

    instances: list[dict] = []
    for reservation in response.get("Reservations", []):
        for instance in reservation.get("Instances", []):
            instances.append(instance)  # type: ignore[arg-type]

    if not instances:
        return CheckResult(
            check_name="Oversized EC2 Instances",
            status=Status.PASS,
            finding="No running EC2 instances found.",
            recommendation="No action required.",
        )

    end_time = datetime.now(tz=timezone.utc)
    start_time = end_time - timedelta(days=14)
    oversized: list[Finding] = []

    for instance in instances:  # type: ignore[assignment]
        instance_id = instance["InstanceId"]
        instance_type = instance["InstanceType"]
        try:
            metrics = cw.get_metric_statistics(
                Namespace="AWS/EC2",
                MetricName="CPUUtilization",
                Dimensions=[{"Name": "InstanceId", "Value": instance_id}],
                StartTime=start_time,
                EndTime=end_time,
                Period=1209600,
                Statistics=["Average"],
            )
            datapoints = metrics.get("Datapoints", [])
            if datapoints:
                avg_cpu = datapoints[0]["Average"]
                if avg_cpu < CPU_THRESHOLD:
                    oversized.append(
                        Finding(instance_id, f"{instance_type}, avg CPU {avg_cpu:.1f}%")
                    )
        except Exception:
            pass

    if not oversized:
        return CheckResult(
            check_name="Oversized EC2 Instances",
            status=Status.PASS,
            finding=f"No obvious right-sizing candidates found among {len(instances)} instance(s).",
            recommendation="No action required.",
        )

    ids = ", ".join(f.resource_id for f in oversized)
    return CheckResult(
        check_name="Oversized EC2 Instances",
        status=Status.WARN,
        finding=f"{len(oversized)} instance(s) with avg CPU < {CPU_THRESHOLD}%: {ids}",
        recommendation=(
            "Use AWS Compute Optimizer or downsize to a smaller"
            " instance type. Savings of 30\u201360% are common."
        ),
        findings=oversized,
    )
