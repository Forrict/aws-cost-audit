# aws-cost-audit

An open-source CLI tool that audits your AWS account for common cost waste patterns and produces actionable findings.

Built by [Forrict](https://forrict.nl) — AWS cloud consultancy in the Netherlands.

## What it does

`aws-cost-audit` scans your AWS account for 15 common cost waste patterns and produces a table of findings with recommendations. Each check is self-contained and gracefully handles missing permissions.

```
aws-cost-audit 0.1.0 — running checks...

  [PASS] Unused EC2 Instances
  [FAIL] Unattached EBS Volumes
  [WARN] Old EBS Snapshots
  [PASS] Idle Load Balancers
  [FAIL] Unattached Elastic IPs
  ...

Check Name                       Status   Finding                                            Recommendation
-------------------------------  -------  -------------------------------------------------  ---------------------------------------------------
Unused EC2 Instances             PASS     No running EC2 instances found.                    No action required.
Unattached EBS Volumes           FAIL     3 unattached volume(s) totalling 300 GiB: ...      Delete volumes that are no longer needed.
Old EBS Snapshots                WARN     12 snapshot(s) older than 90 days (1200 GiB)...    Implement a lifecycle policy using AWS DLM.
...

Summary: 8 PASS | 4 WARN | 2 FAIL | 1 INFO
```

## Checks (15)

| # | Check | What it detects |
|---|-------|-----------------|
| 1 | Unused EC2 Instances | Running instances with avg CPU < 10% over 14 days |
| 2 | Unattached EBS Volumes | Volumes in "available" state (not attached to any instance) |
| 3 | Old EBS Snapshots | Snapshots older than 90 days |
| 4 | Idle Load Balancers | ALBs/NLBs with no healthy targets or zero requests (7 days) |
| 5 | Unattached Elastic IPs | EIPs allocated but not associated |
| 6 | Oversized EC2 Instances | Running instances with avg CPU < 20% (right-sizing candidates) |
| 7 | RI / Savings Plan Coverage | Low commitment coverage vs On-Demand spend |
| 8 | S3 Lifecycle Policies | Buckets without lifecycle rules |
| 9 | Unused NAT Gateways | NAT Gateways with zero traffic (7 days) |
| 10 | CloudWatch Log Retention | Log groups without a retention policy |
| 11 | Idle RDS Instances | RDS instances with < 1 avg connection over 14 days |
| 12 | Previous-Generation Instance Types | EC2 instances on old families (m1, m3, c3, r3, etc.) |
| 13 | Unused Lambda Functions | Functions with 0 invocations over 30 days |
| 14 | Underused DynamoDB Tables | Provisioned tables using < 20% of capacity |
| 15 | Cost Allocation Tags | Resources missing Environment/Project/Owner/CostCenter tags |

## Installation

### Pre-built binaries

Download the latest binary for your platform from [GitHub Releases](https://github.com/Forrict/aws-cost-audit/releases/latest):

**Linux (amd64)**

```bash
curl -Lo aws-cost-audit https://github.com/Forrict/aws-cost-audit/releases/latest/download/aws-cost-audit-linux-amd64
chmod +x aws-cost-audit
sudo mv aws-cost-audit /usr/local/bin/
```

**macOS (Apple Silicon)**

```bash
curl -Lo aws-cost-audit https://github.com/Forrict/aws-cost-audit/releases/latest/download/aws-cost-audit-macos-arm64
chmod +x aws-cost-audit
sudo mv aws-cost-audit /usr/local/bin/
```

**Windows (amd64)**

Download `aws-cost-audit-windows-amd64.exe` from the [releases page](https://github.com/Forrict/aws-cost-audit/releases/latest) and add it to your PATH.

### pip (Python 3.9+)

```bash
pip install aws-cost-audit
```

### From source

```bash
git clone https://github.com/Forrict/aws-cost-audit.git
cd aws-cost-audit
pip install .
```

## Usage

```bash
# Run all checks
aws-cost-audit

# Run with verbose per-resource output
aws-cost-audit --verbose

# Run specific checks only
aws-cost-audit --checks ebs_unattached eip_unattached

# List available checks
aws-cost-audit --list-checks

# Output as JSON (writes to cost-report.json by default)
aws-cost-audit --output json

# Output as CSV (writes to cost-report.csv by default)
aws-cost-audit --output csv

# Write report to a specific file
aws-cost-audit --output json --output-file my-report.json

# Disable color output (useful for CI/logging)
aws-cost-audit --no-color

# Exit code: 0 = all pass, 1 = warnings or failures found
aws-cost-audit && echo "All clean!" || echo "Issues found."
```

## Required IAM Permissions

The tool uses read-only AWS API calls. Attach these permissions to the IAM user or role running the tool:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:DescribeInstances",
        "ec2:DescribeVolumes",
        "ec2:DescribeSnapshots",
        "ec2:DescribeAddresses",
        "ec2:DescribeNatGateways",
        "elasticloadbalancing:DescribeLoadBalancers",
        "elasticloadbalancing:DescribeTargetGroups",
        "elasticloadbalancing:DescribeTargetHealth",
        "cloudwatch:GetMetricStatistics",
        "ce:GetSavingsPlansCoverage",
        "ce:GetReservationCoverage",
        "s3:ListAllMyBuckets",
        "s3:GetBucketLifecycleConfiguration",
        "s3:GetBucketTagging",
        "logs:DescribeLogGroups",
        "rds:DescribeDBInstances",
        "lambda:ListFunctions",
        "dynamodb:ListTables",
        "dynamodb:DescribeTable",
        "sts:GetCallerIdentity"
      ],
      "Resource": "*"
    }
  ]
}
```

## AWS Credentials

The tool uses the default AWS credential chain (environment variables, `~/.aws/credentials`, IAM role, etc.).

```bash
# Using environment variables
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...
export AWS_DEFAULT_REGION=eu-west-1
aws-cost-audit

# Using a named profile
AWS_PROFILE=my-sandbox aws-cost-audit

# Using AWS SSO
aws sso login --profile my-profile
AWS_PROFILE=my-profile aws-cost-audit
```

## Check Descriptions

Detailed descriptions of each check (what it checks, why it matters, typical savings) are in [`check_descriptions.yaml`](check_descriptions.yaml).

## License

MIT — see [LICENSE](LICENSE).

## Contributing

Issues and PRs welcome. Each check lives in `aws_cost_audit/checks/` as a self-contained module with a single `run() -> CheckResult` function.
