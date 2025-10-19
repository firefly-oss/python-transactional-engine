# FireflyTX Test Suite

Comprehensive test suite for the FireflyTX Python wrapper library.

## 🧪 Test Structure

### **Core Tests**

#### [`test_api.py`](test_api.py) ⭐ **NEW**
High-level API testing for the SagaExecutionEngine and convenience functions:
- `SagaExecutionEngine` initialization and configuration
- SAGA registration and execution
- Request/response handling
- Convenience functions (`create_saga_engine`, `execute_saga_once`)

#### [`test_decorators.py`](test_decorators.py)
SAGA and TCC decorator functionality:
- `@saga`, `@saga_step`, `@compensation_step` decorators
- `@step_events` decorator for event configuration
- TCC decorators (`@tcc`, `@try_method`, `@confirm_method`, `@cancel_method`)
- Parameter injection and validation

#### [`test_config.py`](test_config.py)
Configuration generation and validation:
- Java configuration generation
- Engine configuration options
- Event publisher configuration
- Persistence provider configuration

#### [`test_events_persistence_integration.py`](test_events_persistence_integration.py)
Integration testing for events and persistence:
- Event publisher implementations
- Persistence provider implementations
- Configuration integration
- End-to-end event flow

### **Integration Tests**

#### [`test_full_integration.py`](test_full_integration.py)
Complete integration tests against the REAL Java lib-transactional-engine:
- Full SAGA execution workflow (Python defines, Java executes)
- Configuration generation and consumption
- HTTP callback interface between Java and Python
- Error handling and automatic compensation

#### [`test_integration.py`](test_integration.py)
Basic integration testing:
- Core component integration
- API compatibility
- Basic workflow testing

#### [`test_java_bridge.py`](test_java_bridge.py) ⭐ **MOVED**
Java subprocess bridge testing:
- JVM communication
- Method invocation
- Error handling
- Bridge lifecycle management

### **Specialized Tests**

#### [`test_saga_compensation.py`](test_saga_compensation.py)
SAGA compensation logic testing:
- Compensation step execution
- Failure scenarios
- Rollback mechanisms
- Complex dependency handling

#### [`test_utils.py`](test_utils.py)
Utility function testing:
- Type conversion utilities
- Helper functions
- Common algorithms
- Validation utilities

## 🚀 Running Tests

### **Prerequisites**
```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-mock

# Or install development dependencies
pip install -r requirements-dev.txt
```

### **Run All Tests**
```bash
# From project root
pytest tests/

# With verbose output
pytest tests/ -v

# With coverage
pytest tests/ --cov=fireflytx --cov-report=html
```

### **Run Specific Test Categories**

```bash
# Core API tests
pytest tests/test_api.py -v

# Decorator tests
pytest tests/test_decorators.py -v

# Integration tests only
pytest tests/test_*integration*.py -v

# Java bridge tests (requires Java setup)
pytest tests/test_java_bridge.py -v
```

### **Run Tests by Pattern**
```bash
# Test specific functionality
pytest tests/ -k "test_saga" -v
pytest tests/ -k "test_config" -v
pytest tests/ -k "test_event" -v

# Test async functionality
pytest tests/ -k "async" -v

# Skip integration tests (for CI)
pytest tests/ -k "not integration" -v
```

### **Run Tests with Different Outputs**
```bash
# JUnit XML output
pytest tests/ --junit-xml=test-results.xml

# JSON output
pytest tests/ --json-report --json-report-file=test-results.json

# HTML coverage report
pytest tests/ --cov=fireflytx --cov-report=html
```

## 📊 Test Coverage

Current test coverage targets:

- **Core API**: ✅ 95%+ coverage
- **Decorators**: ✅ 90%+ coverage
- **Configuration**: ✅ 85%+ coverage
- **Events & Persistence**: ✅ 80%+ coverage
- **Integration**: ✅ 70%+ coverage (mocked components)

### **Generate Coverage Report**
```bash
# Run tests with coverage
pytest tests/ --cov=fireflytx

# Generate HTML report
pytest tests/ --cov=fireflytx --cov-report=html
open htmlcov/index.html

# Generate terminal report
pytest tests/ --cov=fireflytx --cov-report=term-missing
```

## 🔧 Test Configuration

### **pytest.ini Configuration**
The project includes a `pytest.ini` file with standard configuration:

```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    -v
    --tb=short
    --strict-markers
asyncio_mode = auto
markers =
    integration: Integration tests (may require external dependencies)
    slow: Slow tests (may take longer to run)
    java: Tests requiring Java/JVM setup
```

### **Test Environment Variables**
```bash
# Enable debug logging during tests
export FIREFLYTX_LOG_LEVEL=DEBUG

# Use test-specific configuration
export FIREFLYTX_TEST_MODE=1

# NOTE: Integration tests default to using the REAL Java engine.
# Only set SKIP_JAVA_TESTS=1 temporarily if you need to bypass Java during
# local development (not used in CI and not recommended by default).
# export SKIP_JAVA_TESTS=1
```

## 🧩 Real Engine Usage and Mocking Guidelines

- Integration tests execute against the REAL lib-transactional-engine via the Java subprocess bridge. Do not mock the Java engine in integration tests.
- Unit tests may mock Python-level components (e.g., event publishers, persistence providers) to isolate behavior.
- Avoid external network calls unrelated to the engine in tests; keep tests deterministic and fast where possible.
- Async tests use pytest-asyncio; mark them with @pytest.mark.asyncio as appropriate.

## 📈 Continuous Integration

### **GitHub Actions Integration**
```yaml
# .github/workflows/test.yml
- name: Run tests
  run: |
    pytest tests/ --cov=fireflytx --cov-report=xml
    
- name: Upload coverage
  uses: codecov/codecov-action@v3
  with:
    file: ./coverage.xml
```

### **Local CI Simulation**
```bash
# Simulate CI environment
export CI=true
export SKIP_JAVA_TESTS=1

# Run tests like CI
pytest tests/ --cov=fireflytx --cov-report=xml --junit-xml=results.xml
```

## 🤝 Contributing Tests

### **Adding New Tests**

1. **Follow naming convention**: `test_{component}_{functionality}.py`
2. **Use descriptive test names**: `test_saga_execution_with_compensation`
3. **Include docstrings**: Explain what the test validates
4. **Mock external dependencies**: Avoid real Java/network calls
5. **Test both success and failure cases**

### **Test Organization**
```python
class TestSagaExecution:
    """Test SAGA execution functionality."""
    
    def test_basic_execution(self):
        """Test basic SAGA execution flow."""
        pass
    
    def test_execution_with_failure(self):
        """Test SAGA execution with step failure."""
        pass
    
    # Async example
    async def test_async_execution(self):
        """Test async SAGA execution."""
        pass
```

## 📚 Additional Resources

- **Main Documentation**: [../README.md](../README.md)
- **Examples**: [../examples/README.md](../examples/README.md)
- **API Reference**: [../docs/api-reference.md](../docs/api-reference.md)
- **Development Setup**: [../docs/development.md](../docs/development.md)