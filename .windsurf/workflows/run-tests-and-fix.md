# /run-tests-and-fix

Automated workflow to run tests and fix errors before committing, merging, or deploying.

## Steps

1. **Run all tests to check current status**
   ```bash
   python -m pytest tests/ -v --tb=short
   ```

2. **Analyze test results**
   - Count passed, failed, and skipped tests
   - Identify common failure patterns
   - Categorize errors by type (import errors, type errors, assertion errors, etc.)

3. **For each failed test, do the following:**
   a. Read the test file to understand what's being tested
   b. Read the source file that's being tested
   c. Analyze the error message and identify the root cause
   d. If it's a simple fix (missing import, typo, type error), fix it immediately
   e. If it's a complex issue, ask for clarification or suggest a solution
   f. After fixing, re-run the specific test to verify the fix

4. **Run full test suite again**
   ```bash
   python -m pytest tests/ -v --tb=short
   ```

5. **If all tests pass:**
   - Generate a summary of what was fixed
   - Suggest committing the changes with a descriptive message
   - Provide coverage report if requested

6. **If tests still fail:**
   - Provide detailed analysis of remaining failures
   - Suggest next steps for resolution
   - Ask for user input on how to proceed

## Coverage Report (Optional)

If you want to see code coverage:
```bash
python -m pytest tests/ --cov=src/fastapi_easy --cov-report=term-missing
```

## Test Levels

You can run specific test levels:

- **Unit tests only**: `python -m pytest tests/ -m unit -v`
- **Integration tests only**: `python -m pytest tests/ -m integration -v`
- **E2E tests only**: `python -m pytest tests/ -m e2e -v`

## Best Practices

- Always run tests before committing
- Fix one error at a time
- Re-run tests after each fix to ensure no regressions
- Keep test output for documentation
- Update tests when fixing bugs to prevent regressions
