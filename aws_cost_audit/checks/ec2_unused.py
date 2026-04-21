"""Check 1: Unused EC2 instances (low CPU < 10% avg over 14 days)."""

from datetime import datetime, timedelta, timezone

import boto3

from aws_cost_audit.models import CheckResult, Finding, Status


def run() -> CheckResult:
    ec2 = boto3.client("ec2")
    cw = boto3.client("cloudwatch")

    try:
        instances: list[str] = []
        paginator = ec2.get_paginator("describe_instances")
        for page in paginator.paginate(
            Filters=[{"Name": "instance-state-name", "Values": ["running"]}]
        ):
            for reservation in page.get("Reservations", []):
                for instance in reservation.get("Instances", []):
                    instances.append(instance["InstanceId"])
    except Exception as e:
        return CheckResult(
            check_name="Unused EC2 Instances",
            status=Status.INFO,
            finding=f"Could not retrieve EC2 instances: {e}",
            recommendation=(
                "Ensure IAM permissions include"
                " ec2:DescribeInstances and"
                " cloudwatch:GetMetricStatistics."
            ),
        )

    if not instances:
        return CheckResult(
            check_name="Unused EC2 Instances",
            status=Status.PASS,
            finding="No running EC2 instances found.",
            recommendation="No action required.",
        )

    end_time = datetime.now(tz=timezone.utc)
    start_time = end_time - timedelta(days=14)
    low_cpu: list[Finding] = []

    for instance_id in instances:
        try:
            metrics = cw.get_metric_statistics(
                Namespace="AWS/EC2",
                MetricName="CPUUtilization",
                Dimensions=[{"Name": "InstanceId", "Value": instance_id}],
                StartTime=start_time,
                EndTime=end_time,
                Period=1209600,  # 14 days in seconds
                Statistics=["Average"],
            )
            datapoints = metrics.get("Datapoints", [])
            if datapoints:
                avg_cpu = datapoints[0]["Average"]
                if avg_cpu < 10.0:
                    low_cpu.append(Finding(instance_id, f"avg CPU {avg_cpu:.1f}%"))
            # No datapoints = no metrics = likely idle (no traffic at all)
            else:
                low_cpu.append(Finding(instance_id, "no CPU metrics (0% utilization)"))
        except Exception:
            pass

    if not low_cpu:
        return CheckResult(
            check_name="Unused EC2 Instances",
            status=Status.PASS,
            finding=f"All {len(instances)} running instance(s) have CPU utilization ≥ 10%.",
            recommendation="No action required.",
        )

    ids = ", ".join(f.resource_id for f in low_cpu)
    return CheckResult(
        check_name="Unused EC2 Instances",
        status=Status.WARN,
        finding=f"{len(low_cpu)} instance(s) with avg CPU < 10% over 14 days: {ids}",
        recommendation=(
            "Review instances and stop/terminate if unused."
            " Consider Reserved Instances or Savings Plans"
            " for steady workloads."
        ),
        findings=low_cpu,
    )
