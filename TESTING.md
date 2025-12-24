# Testing Guide

## Overview

The scenario tests are designed to run without calling any LLMs. They validate:
- Scenario normalization and validation rules.
- Deterministic scoring behavior under different match modes.
- Summary table ordering and fields.
- CLI and API behavior for `--summary` vs detailed outputs.

## Install Dependencies

```bash
python -m pip install -r requirements.txt
```

## Run Tests

```bash
python -m pytest
```

## Notes

- API tests set `DATABASE_URL`, `LLM_PROVIDER`, and `OPENAI_API_KEY` internally to avoid configuration failures.
- No external network calls are made during tests.
- What-if tests do not depend on existing databases or data files.
