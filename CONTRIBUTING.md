# Contributing to AWS Cost Optimization Dashboard

Thank you for your interest in contributing to the AWS Cost Optimization Dashboard project! This document provides guidelines for contributing to the project.

## Code of Conduct

This project adheres to a code of conduct. By participating, you are expected to uphold this code.

## How to Contribute

### Reporting Issues

Before creating an issue, please:
1. Check if the issue already exists in the GitHub Issues
2. Provide a clear and descriptive title
3. Include steps to reproduce the issue
4. Provide your environment details (Terraform version, AWS CLI version, etc.)

### Submitting Changes

1. **Fork the repository**
2. **Create a feature branch** from `main`
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Make your changes** following the coding standards
4. **Test your changes** thoroughly
5. **Commit your changes** with descriptive commit messages
6. **Push to your fork** and submit a pull request

### Pull Request Guidelines

- Provide a clear description of the changes
- Include any relevant issue numbers
- Ensure all tests pass
- Update documentation as needed
- Follow the existing code style

## Development Setup

### Prerequisites
- AWS CLI configured with appropriate permissions
- Terraform >= 1.5.0
- Python 3.11+
- Git

### Local Development
```bash
# Clone your fork
git clone https://github.com/your-username/aws-cost-optimization-dashboard.git
cd aws-cost-optimization-dashboard

# Install development dependencies
pip install -r lambda/requirements.txt
pip install pytest black pylint

# Run tests
pytest tests/

# Format code
black lambda/
terraform fmt
```

## Coding Standards

### Terraform
- Use consistent naming conventions
- Include descriptions for all variables and outputs
- Use appropriate resource tags
- Follow security best practices

### Python
- Follow PEP 8 style guidelines
- Use type hints where appropriate
- Include docstrings for functions and classes
- Handle errors gracefully

### Documentation
- Update README.md for significant changes
- Include inline comments for complex logic
- Provide examples for new features

## Testing

### Unit Tests
```bash
# Run Python unit tests
pytest tests/unit/

# Run Terraform validation
terraform validate
terraform plan
```

### Integration Tests
```bash
# Run integration tests (requires AWS credentials)
pytest tests/integration/
```

## Release Process

1. Update version numbers
2. Update CHANGELOG.md
3. Create a pull request to main
4. After merge, create a release tag
5. Update documentation

## Questions?

If you have questions about contributing, please:
1. Check the existing documentation
2. Search through existing issues
3. Create a new issue with the "question" label