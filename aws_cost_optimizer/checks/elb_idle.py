"""Check 4: Idle Elastic Load Balancers (no healthy targets or zero requests)."""

from datetime import datetime, timedelta, timezone

import boto3

from aws_cost_optimizer.models import CheckResult, Finding, Status


def run() -> CheckResult:
    elbv2 = boto3.client("elbv2")
    cw = boto3.client("cloudwatch")

    try:
        lb_response = elbv2.describe_load_balancers()
    except Exception as e:
        return CheckResult(
            check_name="Idle Load Balancers",
            status=Status.INFO,
            finding=f"Could not retrieve load balancers: {e}",
            recommendation="Ensure IAM permissions include elasticloadbalancing:DescribeLoadBalancers.",
        )

    load_balancers = lb_response.get("LoadBalancers", [])
    if not load_balancers:
        return CheckResult(
            check_name="Idle Load Balancers",
            status=Status.PASS,
            finding="No load balancers found.",
            recommendation="No action required.",
        )

    end_time = datetime.now(tz=timezone.utc)
    start_time = end_time - timedelta(days=7)
    idle: list[Finding] = []

    for lb in load_balancers:
        lb_arn = lb["LoadBalancerArn"]
        lb_name = lb["LoadBalancerName"]
        lb_type = lb["Type"]

        # Check for healthy targets
        try:
            tg_resp = elbv2.describe_target_groups(LoadBalancerArn=lb_arn)
            target_groups = tg_resp.get("TargetGroups", [])
            has_healthy = False
            for tg in target_groups:
                health = elbv2.describe_target_health(TargetGroupArn=tg["TargetGroupArn"])
                if any(
                    t["TargetHealth"]["State"] == "healthy"
                    for t in health.get("TargetHealthDescriptions", [])
                ):
                    has_healthy = True
                    break

            if not has_healthy and target_groups:
                idle.append(Finding(lb_name, "no healthy targets"))
                continue
        except Exception:
            pass

        # Check request count over 7 days
        try:
            metric_name = "RequestCount" if lb_type in ("application",) else "ActiveFlowCount"
            dim_name = "LoadBalancer"
            dim_value = lb_arn.split("loadbalancer/")[-1]
            metrics = cw.get_metric_statistics(
                Namespace="AWS/ApplicationELB" if lb_type == "application" else "AWS/NetworkELB",
                MetricName=metric_name,
                Dimensions=[{"Name": dim_name, "Value": dim_value}],
                StartTime=start_time,
                EndTime=end_time,
                Period=604800,
                Statistics=["Sum"],
            )
            datapoints = metrics.get("Datapoints", [])
            total = sum(d["Sum"] for d in datapoints) if datapoints else 0
            if total == 0:
                idle.append(Finding(lb_name, "zero requests in last 7 days"))
        except Exception:
            pass

    if not idle:
        return CheckResult(
            check_name="Idle Load Balancers",
            status=Status.PASS,
            finding=f"All {len(load_balancers)} load balancer(s) appear active.",
            recommendation="No action required.",
        )

    names = ", ".join(f.resource_id for f in idle)
    return CheckResult(
        check_name="Idle Load Balancers",
        status=Status.WARN,
        finding=f"{len(idle)} idle load balancer(s): {names}",
        recommendation="Delete idle load balancers to avoid hourly charges (~$16–$20/month per ALB).",
        findings=idle,
    )
