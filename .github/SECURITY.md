# Security Policy

## Supported Versions

| Version | Supported |
|---|---|
| 1.x | ✓ |

---

## Reporting a Vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

Report vulnerabilities privately by emailing:

**sgayatrisravya@gmail.com**

Include in your report:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

---

## What to expect

- Acknowledgement within 48 hours
- Status update within 7 days
- Fix released as soon as possible depending on severity

---

## Scope

### In scope

- Python SDK (`sdks/python`)
- Python CLI (`cli`)
- Java SDK (`sdks/java`)
- Redis schema design

### Out of scope

- Redis itself — report to Redis
- Your Redis configuration or network setup
- Third party dependencies — report to their maintainers

---

## Disclosure policy

Once a fix is released:

1. Security advisory published on GitHub
2. CHANGELOG updated with CVE reference if applicable
3. PyPI and Maven packages updated

Please allow us to release a fix before publicly disclosing the vulnerability.