"""Check 7: Missing Reserved Instance / Savings Plan coverage."""

from datetime import datetime, timedelta, timezone

import boto3

from aws_cost_optimizer.models import CheckResult, Finding, Status


def run() -> CheckResult:
    ce = boto3.client("ce")

    end_date = datetime.now(tz=timezone.utc).date()
    start_date = end_date - timedelta(days=30)

    try:
        # Check Savings Plans coverage
        sp_response = ce.get_savings_plans_coverage(
            TimePeriod={"Start": str(start_date), "End": str(end_date)},
            Granularity="MONTHLY",
        )
        sp_coverages = sp_response.get("SavingsPlansCoverages", [])
        sp_coverage_pct = 0.0
        if sp_coverages:
            total = sp_coverages[0].get("Coverage", {})
            sp_coverage_pct = float(total.get("CoveragePercentage", 0))
    except Exception:
        sp_coverage_pct = None  # type: ignore[assignment]

    try:
        # Check RI coverage
        ri_response = ce.get_reservation_coverage(
            TimePeriod={"Start": str(start_date), "End": str(end_date)},
            Granularity="MONTHLY",
        )
        ri_coverages = ri_response.get("CoveragesByTime", [])
        ri_coverage_pct = 0.0
        if ri_coverages:
            ri_total = ri_coverages[0].get("Total", {})
            ri_coverage_pct = float(
                ri_total.get("CoverageHours", {}).get("CoverageHoursPercentage", 0)  # type: ignore[union-attr]
            )
    except Exception:
        ri_coverage_pct = None  # type: ignore[assignment]

    if sp_coverage_pct is None and ri_coverage_pct is None:
        return CheckResult(
            check_name="RI / Savings Plan Coverage",
            status=Status.INFO,
            finding="Could not retrieve coverage data from Cost Explorer.",
            recommendation=(
                "Ensure IAM permissions include"
                " ce:GetSavingsPlansCoverage and"
                " ce:GetReservationCoverage."
            ),
        )

    findings = []
    if sp_coverage_pct is not None:
        findings.append(Finding("SavingsPlans", f"{sp_coverage_pct:.1f}% coverage (last 30 days)"))
    if ri_coverage_pct is not None:
        findings.append(
            Finding("ReservedInstances", f"{ri_coverage_pct:.1f}% coverage (last 30 days)")
        )

    # Use the BEST (max) of SP or RI coverage, because you cannot combine
    # Savings Plans and Reserved Instances on the same resource — either one
    # covering the spend is sufficient.
    available = [p for p in (sp_coverage_pct, ri_coverage_pct) if p is not None]
    best_pct = max(available) if available else 0.0

    if best_pct >= 70:
        status = Status.PASS
        rec = "Coverage looks healthy. Review annually to ensure commitments still match usage."
    elif best_pct >= 20:
        status = Status.WARN
        rec = (
            "Moderate commitment coverage. Consider purchasing"
            " additional Reserved Instances or Savings Plans"
            " for predictable workloads. Savings of 30\u201372% over On-Demand."
        )
    else:
        status = Status.FAIL
        rec = (
            "Very low commitment coverage. Evaluate Compute"
            " Savings Plans for immediate savings of up to"
            " 66% with maximum flexibility."
        )

    detail = "; ".join(f"{f.resource_id}: {f.detail}" for f in findings)
    return CheckResult(
        check_name="RI / Savings Plan Coverage",
        status=status,
        finding=detail or "No coverage data available.",
        recommendation=rec,
        findings=findings,
    )
