"""AWS Cost Optimizer CLI entry point."""

from __future__ import annotations

import argparse
import sys

from tabulate import tabulate  # type: ignore[import-untyped]

from aws_cost_optimizer import __version__
from aws_cost_optimizer.models import CheckResult, Status

# Registry of all checks in order
CHECK_MODULES = [
    ("ec2_unused", "Unused EC2 Instances"),
    ("ebs_unattached", "Unattached EBS Volumes"),
    ("ebs_old_snapshots", "Old EBS Snapshots"),
    ("elb_idle", "Idle Load Balancers"),
    ("eip_unattached", "Unattached Elastic IPs"),
    ("ec2_rightsizing", "Oversized EC2 Instances"),
    ("ri_coverage", "RI / Savings Plan Coverage"),
    ("s3_lifecycle", "S3 Lifecycle Policies"),
    ("nat_gateway_unused", "Unused NAT Gateways"),
    ("cloudwatch_log_retention", "CloudWatch Log Retention"),
    ("rds_idle", "Idle RDS Instances"),
    ("ec2_previous_gen", "Previous-Generation Instance Types"),
    ("lambda_unused", "Unused Lambda Functions"),
    ("dynamodb_underused", "Underused DynamoDB Tables"),
    ("cost_allocation_tags", "Cost Allocation Tags"),
]

STATUS_COLORS = {
    Status.PASS: "\033[92m",  # green
    Status.WARN: "\033[93m",  # yellow
    Status.FAIL: "\033[91m",  # red
    Status.INFO: "\033[94m",  # blue
}
RESET = "\033[0m"


def _colorize(text: str, status: Status, use_color: bool) -> str:
    if not use_color:
        return text
    return f"{STATUS_COLORS.get(status, '')}{text}{RESET}"


def run_checks(only: list[str] | None = None) -> list[CheckResult]:
    import importlib

    results: list[CheckResult] = []
    for module_name, _ in CHECK_MODULES:
        if only and module_name not in only:
            continue
        try:
            mod = importlib.import_module(f"aws_cost_optimizer.checks.{module_name}")
            result = mod.run()
        except Exception as e:
            result = CheckResult(
                check_name=module_name.replace("_", " ").title(),
                status=Status.INFO,
                finding=f"Check failed with error: {e}",
                recommendation="Review IAM permissions and AWS connectivity.",
            )
        results.append(result)
        # Stream output as checks run
        status_str = result.status.value
        print(f"  [{status_str}] {result.check_name}")

    return results


def print_report(results: list[CheckResult], use_color: bool = True, verbose: bool = False) -> None:
    print()
    rows = []
    for r in results:
        status_str = _colorize(r.status.value, r.status, use_color)
        rows.append([r.check_name, status_str, r.finding, r.recommendation])

    headers = ["Check Name", "Status", "Finding", "Recommendation"]
    print(tabulate(rows, headers=headers, tablefmt="simple", maxcolwidths=[30, 6, 50, 50]))

    if verbose:
        print()
        for r in results:
            if r.findings:
                print(f"\n--- {r.check_name} Details ---")
                for f in r.findings:
                    print(f"  • {f.resource_id}: {f.detail}")

    print()
    passes = sum(1 for r in results if r.status == Status.PASS)
    warns = sum(1 for r in results if r.status == Status.WARN)
    fails = sum(1 for r in results if r.status == Status.FAIL)
    infos = sum(1 for r in results if r.status == Status.INFO)

    summary_parts = []
    if passes:
        summary_parts.append(_colorize(f"{passes} PASS", Status.PASS, use_color))
    if warns:
        summary_parts.append(_colorize(f"{warns} WARN", Status.WARN, use_color))
    if fails:
        summary_parts.append(_colorize(f"{fails} FAIL", Status.FAIL, use_color))
    if infos:
        summary_parts.append(_colorize(f"{infos} INFO", Status.INFO, use_color))
    print(f"Summary: {' | '.join(summary_parts)}")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="aws-cost-optimizer",
        description="Run AWS cost optimization checks against your account.",
    )
    parser.add_argument("--version", action="version", version=f"aws-cost-optimizer {__version__}")
    parser.add_argument("--no-color", action="store_true", help="Disable ANSI color output")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show per-resource findings")
    parser.add_argument(
        "--checks",
        nargs="+",
        metavar="CHECK",
        help="Run only specific checks (module names, e.g. ebs_unattached ec2_unused)",
    )
    parser.add_argument("--list-checks", action="store_true", help="List available checks and exit")
    args = parser.parse_args()

    if args.list_checks:
        print("Available checks:")
        for module_name, description in CHECK_MODULES:
            print(f"  {module_name:<30} {description}")
        sys.exit(0)

    use_color = not args.no_color and sys.stdout.isatty()

    print(f"aws-cost-optimizer {__version__} — running checks...\n")
    results = run_checks(only=args.checks)
    print_report(results, use_color=use_color, verbose=args.verbose)

    # Exit code: 0 = all pass/info, 1 = any warn/fail
    has_issues = any(r.status in (Status.WARN, Status.FAIL) for r in results)
    sys.exit(1 if has_issues else 0)


if __name__ == "__main__":
    main()
