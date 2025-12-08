# FastAPI-Easy Testing Guide

This comprehensive guide covers testing strategies, best practices, and optimization techniques for the FastAPI-Easy project.

## Table of Contents

1. [Testing Philosophy](#testing-philosophy)
2. [Test Structure](#test-structure)
3. [Test Types](#test-types)
4. [Best Practices](#best-practices)
5. [Performance Testing](#performance-testing)
6. [Mocking Strategies](#mocking-strategies)
7. [Async Testing](#async-testing)
8. [Database Testing](#database-testing)
9. [CI/CD Integration](#cicd-integration)
10. [Troubleshooting](#troubleshooting)

## Testing Philosophy

### Test Pyramid

We follow the test pyramid principle:

```
        /\
       /E2E\      <- Few, high-value end-to-end tests
      /------\
     /Integr. \   <- Moderate integration tests
    /----------\
   /   Unit     \ <- Many, fast, focused unit tests
  /--------------\
```

- **Unit Tests (70%)**: Fast, isolated tests for individual functions and classes
- **Integration Tests (20%)**: Tests component interactions
- **E2E Tests (10%)**: Full workflow tests

### Testing Goals

1. **Fast Feedback**: Tests should run quickly
2. **Reliability**: Tests should be deterministic
3. **Maintainability**: Tests should be easy to understand and modify
4. **Coverage**: Critical paths should be well-tested

## Test Structure

### Directory Organization

```
tests/
├── unit/                    # Unit tests
│   ├── test_utils/         # Utility function tests
│   ├── test_migrations/    # Migration system tests
│   ├── test_security/      # Security feature tests
│   └── test_backends/      # Database backend tests
├── integration/            # Integration tests
│   ├── test_sqlalchemy/    # SQLAlchemy integration
│   ├── test_tortoise/      # Tortoise ORM integration
│   └── test_transactions/  # Transaction handling
├── performance/            # Performance tests
│   ├── test_concurrent/    # Concurrency tests
│   └── test_memory/        # Memory usage tests
├── e2e/                    # End-to-end tests
│   └── test_api/           # API endpoint tests
├── conftest.py            # Shared fixtures
└── conftest_improved.py   # Enhanced fixtures
```

### Test Naming Conventions

- **Files**: `test_<module_name>.py`
- **Classes**: `Test<FeatureName>` or `Test<ClassName>`
- **Methods**: `test_<functionality>` with descriptive names

```python
# Good
class TestMigrationEngineErrorHandling:
    def test_storage_error_handling(self):
        pass

    def test_lock_acquisition_timeout(self):
        pass

# Bad
class TestMigration:
    def test_error1(self):
        pass

    def test_lock(self):
        pass
```

## Test Types

### Unit Tests

Unit tests test individual components in isolation.

**Example:**
```python
@pytest.mark.unit
class TestQueryParams:
    def test_simple_parameter_parsing(self):
        """Test basic parameter parsing"""
        dependency = QueryParams(SimpleQuery)
        result = dependency(name="John", age="30")
        assert result.name == "John"
        assert result.age == 30
```

### Integration Tests

Integration tests test component interactions.

**Example:**
```python
@pytest.mark.integration
@pytest.mark.asyncio
class TestMigrationIntegration:
    async def test_full_migration_workflow(self, migration_engine):
        """Test complete migration workflow"""
        # Create initial schema
        metadata = MetaData()
        # ... setup

        # Run migration
        result = await migration_engine.auto_migrate()

        # Verify results
        assert result.status == "success"
```

### Performance Tests

Performance tests ensure code meets performance requirements.

**Example:**
```python
@pytest.mark.performance
@pytest.mark.benchmark
def test_query_parsing_performance(benchmark):
    """Benchmark query parameter parsing"""
    dependency = QueryParams(ComplexQuery)

    result = benchmark(dependency, **test_params)
    assert result is not None
```

## Best Practices

### 1. Test Isolation

Each test should be independent:

```python
# Good - Isolated test
@pytest.fixture
def clean_engine():
    engine = create_engine("sqlite:///:memory:")
    yield engine
    engine.dispose()

def test_feature(clean_engine):
    # Test with clean state
    pass

# Bad - Shared state
shared_engine = create_engine("sqlite:///:memory:")

def test_feature1():
    # Modifies shared_engine
    pass

def test_feature2():
    # Depends on test_feature1 state
    pass
```

### 2. Descriptive Test Names

Test names should describe what and why:

```python
# Good
def test_query_parameter_validation_raises_error_with_invalid_type():
    """Test that validation error is raised for invalid parameter types"""

def test_migration_engine_handles_lock_timeout_gracefully():
    """Test graceful handling of lock acquisition timeout"""

# Bad
def test_query_params():
    """Test query params"""

def test_migration():
    """Test migration"""
```

### 3. Use Fixtures for Setup

Use fixtures for common test setup:

```python
@pytest.fixture
def sample_migration():
    """Create sample migration for testing"""
    return Migration(
        version="20240101_001",
        description="Test migration",
        upgrade_sql="CREATE TABLE test (id INTEGER);",
        downgrade_sql="DROP TABLE test;",
        risk_level=RiskLevel.SAFE,
    )

def test_migration_processing(sample_migration):
    result = process_migration(sample_migration)
    assert result is not None
```

### 4. Proper Async Testing

Use proper async testing patterns:

```python
# Good - Proper async test
@pytest.mark.asyncio
async def test_async_operation(async_migration_engine):
    result = await async_migration_engine.auto_migrate()
    assert result.status == "success"

# Bad - Mixing sync/async improperly
def test_async_operation():
    loop = asyncio.get_event_loop()
    result = loop.run_until_complete(async_operation())
    # This can cause issues with test isolation
```

### 5. Mock External Dependencies

Mock external dependencies for isolated testing:

```python
@patch('fastapi_easy.migrations.engine.logger')
def test_error_logging(mock_logger, migration_engine):
    """Test that errors are properly logged"""
    # Trigger error condition
    with pytest.raises(Exception):
        await migration_engine.auto_migrate()

    # Verify logging
    mock_logger.error.assert_called_once()
```

## Performance Testing

### Benchmarking

Use pytest-benchmark for performance testing:

```python
@pytest.mark.benchmark
def test_serialization_performance(benchmark):
    """Benchmark JSON serialization performance"""
    data = generate_large_dataset()

    result = benchmark(json.dumps, data)
    assert len(result) > 0
```

### Memory Testing

Test memory usage with memory_profiler:

```python
@memory_profiler.profile
def test_memory_efficiency():
    """Test function memory efficiency"""
    process_large_dataset()
    # Memory usage will be profiled
```

### Concurrency Testing

Test concurrent operations:

```python
@pytest.mark.asyncio
async def test_concurrent_migrations(parallel_test_runner):
    """Test migration engine under concurrent load"""
    tasks = [run_migration() for _ in range(10)]
    results = await asyncio.gather(*tasks)

    # Verify all completed successfully
    assert all(r.status == "success" for r in results)
```

## Mocking Strategies

### 1. Mock Databases

Use in-memory databases for testing:

```python
@pytest.fixture
def test_database():
    """Create test database"""
    engine = create_engine("sqlite:///:memory:")
    yield engine
    engine.dispose()
```

### 2. Mock External Services

```python
@patch('requests.get')
def test_external_api_call(mock_get):
    """Test handling of external API calls"""
    mock_get.return_value.json.return_value = {"status": "ok"}

    result = fetch_external_data()
    assert result["status"] == "ok"
```

### 3. Mock File System

```python
@pytest.fixture
def temp_fs():
    """Create temporary file system"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)
```

## Async Testing

### Async Fixtures

Create async fixtures with proper setup/teardown:

```python
@pytest.fixture
async def async_migration_engine():
    """Async migration engine fixture"""
    engine = create_engine("sqlite:///:memory:")
    metadata = MetaData()
    migration_engine = MigrationEngine(engine, metadata)

    # Setup
    migration_engine.lock.acquire = AsyncMock(return_value=True)

    yield migration_engine

    # Cleanup
    engine.dispose()
```

### Async Context Managers

Test async context managers:

```python
@pytest.mark.asyncio
async def test_async_context_manager():
    """Test async context manager behavior"""
    async with AsyncResource() as resource:
        assert resource.is_ready()
        result = await resource.process()
        assert result is not None

    # Resource should be cleaned up
    assert resource.is_closed()
```

## Database Testing

### Transaction Rollback

Use transactions for test isolation:

```python
@pytest.fixture
def db_session(test_engine):
    """Create database session with rollback"""
    connection = test_engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(bind=connection)
    session = Session()

    yield session

    session.close()
    transaction.rollback()
    connection.close()
```

### Database Fixtures

Create reusable database fixtures:

```python
@pytest.fixture
def populated_database(db_session):
    """Create database with test data"""
    # Create test records
    user = User(name="Test User", email="test@example.com")
    db_session.add(user)
    db_session.commit()

    return db_session
```

## CI/CD Integration

### GitHub Actions

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.8, 3.9, "3.10", "3.11"]

    steps:
    - uses: actions/checkout@v3
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}

    - name: Install dependencies
      run: |
        pip install -e ".[dev]"

    - name: Run unit tests
      run: |
        pytest tests/unit/ -v --cov=src

    - name: Run integration tests
      run: |
        pytest tests/integration/ -v

    - name: Upload coverage
      uses: codecov/codecov-action@v3
```

### Performance Monitoring

Monitor test performance over time:

```python
# Record performance metrics
@pytest.fixture(autouse=True)
def performance_recording(request):
    """Record test performance metrics"""
    start_time = time.perf_counter()
    start_memory = psutil.Process().memory_info().rss

    yield

    duration = time.perf_counter() - start_time
    memory_delta = psutil.Process().memory_info().rss - start_memory

    # Log or store metrics
    record_test_metrics(
        test_name=request.node.name,
        duration=duration,
        memory_delta=memory_delta
    )
```

## Troubleshooting

### Common Issues

1. **Lock File Conflicts**
   ```python
   # Clean up lock files before tests
   @pytest.fixture(autouse=True)
   def cleanup_locks():
       for lock_file in [".fastapi_easy_migration.lock"]:
           if os.path.exists(lock_file):
               os.remove(lock_file)
   ```

2. **Async Test Isolation**
   ```python
   # Use event loop fixture for proper isolation
   @pytest.fixture
   def event_loop():
       loop = asyncio.new_event_loop()
       yield loop
       loop.close()
   ```

3. **Database Connection Leaks**
   ```python
   # Ensure proper cleanup
   @pytest.fixture(autouse=True)
   def cleanup_connections():
       yield
       # Force close all connections
       from sqlalchemy import event
       for engine in engines:
           engine.dispose()
   ```

### Debugging Tips

1. **Use verbose output**: `pytest -v -s`
2. **Stop on first failure**: `pytest -x`
3. **Run specific tests**: `pytest tests/unit/test_migrations.py::TestMigrationEngine`
4. **Show local variables**: `pytest -l`
5. **Use pdb debugger**: `pytest --pdb`

### Performance Debugging

1. **Profile slow tests**:
   ```python
   @pytest.mark.slow
   def test_slow_operation():
       with profile_context() as profile:
           # Your test code
           pass
   ```

2. **Memory profiling**:
   ```python
   @memory_profiler.profile
   def test_memory_usage():
       # Your test code
       pass
   ```

## Running Tests

### Basic Commands

```bash
# Run all tests
pytest

# Run specific test types
pytest tests/unit/
pytest tests/integration/
pytest tests/performance/

# Run with coverage
pytest --cov=src --cov-report=html

# Run in parallel
pytest -n auto

# Run performance benchmarks
pytest --benchmark-only
```

### Advanced Usage

```bash
# Run tests by marker
pytest -m "unit and not slow"
pytest -m "integration or e2e"

# Generate coverage report
pytest --cov=src --cov-report=term-missing --cov-report=html

# Run performance tests
pytest tests/performance/ --benchmark-only

# Run with custom configuration
pytest -c pytest_optimized.ini
```

## Test Metrics

Track these metrics for test health:

1. **Coverage**: Target >80% line coverage
2. **Duration**: Unit tests <1s, integration <5s
3. **Flakiness**: <1% test failure rate
4. **Memory**: No memory leaks in test suites
5. **Concurrency**: Safe parallel test execution

## Continuous Improvement

Regularly review and improve tests:

1. **Weekly**: Review test failures and flakiness
2. **Monthly**: Review test coverage and performance
3. **Quarterly**: Refactor slow or complex tests
4. **Annually**: Update testing tools and strategies

## Resources

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [pytest-benchmark](https://pytest-benchmark.readthedocs.io/)
- [Testing Best Practices](https://docs.pytest.org/en/stable/explanation/goodpractices.html)

Remember: Good tests are an investment in code quality and maintainability.