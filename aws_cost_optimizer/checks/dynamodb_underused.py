"""Check 14: Unoptimized DynamoDB tables (provisioned but underused)."""

from datetime import datetime, timedelta, timezone

import boto3

from aws_cost_optimizer.models import CheckResult, Finding, Status

UTILIZATION_THRESHOLD = 0.2  # 20% of provisioned capacity


def run() -> CheckResult:
    ddb = boto3.client("dynamodb")
    cw = boto3.client("cloudwatch")

    tables: list[str] = []
    paginator = ddb.get_paginator("list_tables")
    try:
        for page in paginator.paginate():
            tables.extend(page.get("TableNames", []))
    except Exception as e:
        return CheckResult(
            check_name="Underused DynamoDB Tables",
            status=Status.INFO,
            finding=f"Could not list DynamoDB tables: {e}",
            recommendation="Ensure IAM permissions include dynamodb:ListTables.",
        )

    if not tables:
        return CheckResult(
            check_name="Underused DynamoDB Tables",
            status=Status.PASS,
            finding="No DynamoDB tables found.",
            recommendation="No action required.",
        )

    end_time = datetime.now(tz=timezone.utc)
    start_time = end_time - timedelta(days=7)
    underused: list[Finding] = []

    for table_name in tables:
        try:
            desc = ddb.describe_table(TableName=table_name)
            table = desc["Table"]
            billing_mode = table.get("BillingModeSummary", {}).get("BillingMode", "PROVISIONED")
            if billing_mode == "PAY_PER_REQUEST":
                continue  # On-demand tables are already optimized

            provisioned = table.get("ProvisionedThroughput", {})
            read_cap = provisioned.get("ReadCapacityUnits", 0)
            write_cap = provisioned.get("WriteCapacityUnits", 0)
            if read_cap == 0 and write_cap == 0:
                continue

            # Check consumed RCU and WCU
            for metric, cap in [
                ("ConsumedReadCapacityUnits", read_cap),
                ("ConsumedWriteCapacityUnits", write_cap),
            ]:
                if cap == 0:
                    continue
                metrics = cw.get_metric_statistics(
                    Namespace="AWS/DynamoDB",
                    MetricName=metric,
                    Dimensions=[{"Name": "TableName", "Value": table_name}],
                    StartTime=start_time,
                    EndTime=end_time,
                    Period=604800,
                    Statistics=["Sum"],
                )
                datapoints = metrics.get("Datapoints", [])
                consumed = datapoints[0]["Sum"] if datapoints else 0
                provisioned_total = cap * 7 * 24 * 3600  # cap-seconds over 7 days
                utilization = consumed / provisioned_total if provisioned_total > 0 else 0
                if utilization < UTILIZATION_THRESHOLD:
                    underused.append(
                        Finding(
                            table_name,
                            f"{metric}: {utilization * 100:.1f}% utilization (provisioned {cap})",
                        )
                    )
                    break  # One finding per table is enough
        except Exception:
            pass

    if not underused:
        return CheckResult(
            check_name="Underused DynamoDB Tables",
            status=Status.PASS,
            finding=(
                "No significantly underused provisioned DynamoDB"
                f" tables found among {len(tables)} table(s)."
            ),
            recommendation="No action required.",
        )

    names = ", ".join(f.resource_id for f in underused)
    return CheckResult(
        check_name="Underused DynamoDB Tables",
        status=Status.WARN,
        finding=(
            f"{len(underused)} DynamoDB table(s) with"
            f" < {int(UTILIZATION_THRESHOLD * 100)}% capacity"
            f" utilization: {names}"
        ),
        recommendation=(
            "Switch underused tables to on-demand"
            " (PAY_PER_REQUEST) billing or reduce provisioned"
            " capacity. Enable auto-scaling."
        ),
        findings=underused,
    )
