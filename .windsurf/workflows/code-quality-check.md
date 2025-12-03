# /code-quality-check

Automated workflow to check and improve code quality before committing.

## Steps

1. **Run code formatting check with Black**

   ```bash
   black --check src/fastapi_easy
   ```

2. **Run import sorting check with isort**

   ```bash
   isort --check-only src/fastapi_easy
   ```

3. **Run linting with flake8**

   ```bash
   flake8 src/fastapi_easy --count --select=E9,F63,F7,F82 --show-source --statistics
   ```

4. **Run type checking with mypy**

   ```bash
   mypy src/fastapi_easy --ignore-missing-imports
   ```

5. **If any checks fail, ask user if they want to auto-fix:**
   - For Black: `black src/fastapi_easy`
   - For isort: `isort src/fastapi_easy`
   - For flake8: Show specific issues that need manual fixing
   - For mypy: Show type errors that need manual fixing

6. **After fixes, re-run all checks to verify**

7. **Generate a summary report:**
   - List all checks that passed
   - List any remaining issues
   - Provide recommendations for improvement

## Tools Used

- **Black**: Code formatter (PEP 8 compliance)
- **isort**: Import statement sorter
- **flake8**: Style guide enforcement
- **mypy**: Static type checker

## Best Practices

- Run this workflow before committing code
- Fix formatting issues automatically when possible
- Address type errors and linting issues manually
- Keep code style consistent across the project
- Use meaningful commit messages after quality checks
