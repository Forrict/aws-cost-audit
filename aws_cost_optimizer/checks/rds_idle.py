"""Check 11: Idle RDS instances (low connections over 14 days)."""

from datetime import datetime, timedelta, timezone

import boto3

from aws_cost_optimizer.models import CheckResult, Finding, Status

CONNECTION_THRESHOLD = 1.0  # avg connections per datapoint


def run() -> CheckResult:
    rds = boto3.client("rds")
    cw = boto3.client("cloudwatch")

    try:
        response = rds.describe_db_instances()
    except Exception as e:
        return CheckResult(
            check_name="Idle RDS Instances",
            status=Status.INFO,
            finding=f"Could not retrieve RDS instances: {e}",
            recommendation="Ensure IAM permissions include rds:DescribeDBInstances.",
        )

    instances = [
        db for db in response.get("DBInstances", [])
        if db["DBInstanceStatus"] == "available"
    ]

    if not instances:
        return CheckResult(
            check_name="Idle RDS Instances",
            status=Status.PASS,
            finding="No available RDS instances found.",
            recommendation="No action required.",
        )

    end_time = datetime.now(tz=timezone.utc)
    start_time = end_time - timedelta(days=14)
    idle: list[Finding] = []

    for db in instances:
        db_id = db["DBInstanceIdentifier"]
        db_class = db["DBInstanceClass"]
        try:
            metrics = cw.get_metric_statistics(
                Namespace="AWS/RDS",
                MetricName="DatabaseConnections",
                Dimensions=[{"Name": "DBInstanceIdentifier", "Value": db_id}],
                StartTime=start_time,
                EndTime=end_time,
                Period=1209600,
                Statistics=["Average"],
            )
            datapoints = metrics.get("Datapoints", [])
            avg_connections = datapoints[0]["Average"] if datapoints else 0
            if avg_connections < CONNECTION_THRESHOLD:
                idle.append(Finding(db_id, f"{db_class}, avg {avg_connections:.1f} connections"))
        except Exception:
            pass

    if not idle:
        return CheckResult(
            check_name="Idle RDS Instances",
            status=Status.PASS,
            finding=f"All {len(instances)} RDS instance(s) show active connections.",
            recommendation="No action required.",
        )

    ids = ", ".join(f.resource_id for f in idle)
    return CheckResult(
        check_name="Idle RDS Instances",
        status=Status.WARN,
        finding=f"{len(idle)} idle RDS instance(s) with < {CONNECTION_THRESHOLD} avg connections/14d: {ids}",
        recommendation="Stop or delete idle RDS instances. Consider Aurora Serverless for intermittent workloads.",
        findings=idle,
    )
