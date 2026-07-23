# Contributing to AWS Cost Optimization Dashboard

This document explains how to contribute to the project.

## Reporting Issues

Before opening an issue:

1. Check whether the issue already exists in the GitHub Issues list.
2. Provide a clear, descriptive title.
3. Include steps to reproduce the issue.
4. Include your environment details: Terraform version, AWS CLI version, Python version, and OS.

## Submitting Changes

1. Fork the repository.
2. Create a feature branch from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. Make your changes following the coding standards below.
4. Run the test suite and ensure it passes.
5. Commit with a descriptive message.
6. Push to your fork and open a pull request.

## Pull Request Guidelines

- Describe what the change does and why.
- Reference any related issues.
- Ensure all CI checks pass before requesting review.
- Update documentation if the change affects behaviour or configuration.
- Follow the existing code style.

## Development Setup

Requirements:

- AWS CLI configured with appropriate permissions
- Terraform 1.5 or later
- Python 3.11 or later
- Git

Local setup:

```bash
git clone https://github.com/your-username/aws-cost-optimization-dashboard.git
cd aws-cost-optimization-dashboard

pip install pytest black flake8 boto3 urllib3

# Run tests
pytest tests/ -v

# Format code
black lambda/ tests/

# Lint
flake8 lambda/handler.py tests/test_handler.py --max-line-length=88

# Validate Terraform
terraform fmt -check -recursive
terraform init -backend=false
terraform validate
```

## Coding Standards

### Python

- Follow PEP 8.
- Format with Black (line length 88).
- Lint with Flake8.
- Add type hints to all function signatures.
- Write a docstring for every function.
- Handle errors explicitly; avoid bare `except` clauses.

### Terraform

- Run `terraform fmt` before committing.
- Include `description` on all variables and outputs.
- Scope IAM permissions to specific resource ARNs, not wildcards.
- Use `var.environment` in resource names for multi-environment compatibility.

### Documentation

- Update `README.md` for any change that affects setup, configuration, or behaviour.
- Update `CHANGELOG.md` under the appropriate version section.
- Add inline comments for non-obvious logic.

## Running Tests

```bash
pytest tests/ -v --tb=short
```

All 24 tests must pass. The tests use mocked AWS clients and do not require
AWS credentials or network access.

## Release Process

1. Update `CHANGELOG.md` with the new version and release date.
2. Open a pull request to `main`.
3. After merge, create a release tag following semantic versioning (e.g. `v2.1.0`).
4. Update documentation if the release includes breaking changes.

## Questions

If something is unclear:

1. Check the existing documentation in the `docs/` directory.
2. Search the existing GitHub Issues.
3. Open a new issue with the label `question`.
