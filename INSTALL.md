# Installation Guide - Python Defines, Java Executes Architecture

This guide covers the installation and setup of the Firefly Transactional Engine with the "Python defines, Java executes" architecture.

## Prerequisites

### Required

- **Python 3.9+**: The Python environment for development
- **Java 11+**: Required for the Java lib-transactional-engine execution
  - OpenJDK 11, 17, or 21 recommended
  - Oracle JDK also supported

### Optional (for development)

- **Maven 3.6+**: For building the Java subprocess bridge (optional - will use javac fallback)
- **Git**: For downloading lib-transactional-engine sources

## Quick Installation

> **⚠️ Important:** FireflyTX is not published to PyPI. You must install from source or use the install script.

### Method 1: Using the Install Script (Recommended)

```bash
curl -fsSL https://raw.githubusercontent.com/firefly-oss/python-transactional-engine/main/install.sh | bash
```

This automated script will:
1. Check system requirements (Python 3.9+, Java 11+)
2. Clone the repository from GitHub
3. Install FireflyTX and all dependencies
4. Download/build lib-transactional-engine JAR
5. Verify the installation
6. Show you next steps

### Method 2: Manual Installation from Source

```bash
# Clone the repository
git clone https://github.com/firefly-oss/python-transactional-engine.git
cd python-transactional-engine

# Install in regular mode
pip install .

# OR install in development/editable mode
pip install -e .
```

This will:
1. Install the Python package and dependencies
2. Automatically build the Java subprocess bridge during installation
3. Set up the lib-transactional-engine download system

## Architecture Overview

The installation sets up a hybrid architecture:

```
┌─────────────────────────────────────────────────────────────────┐
│                     Installation Process                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. Python Package Installation                                 │
│     └── fireflytx Python modules                                │
│                                                                 │
│  2. Java Subprocess Bridge Build                                │
│     └── java-subprocess-bridge.jar                              │
│         ├── JavaSubprocessBridge.class                          │
│         ├── PythonCallbackHandler.class                         │
│         ├── SagaDefinition.class                                │
│         └── JSON communication protocol                         │
│                                                                 │
│  3. lib-transactional-engine Setup                              │
│     └── Automatic download and build from GitHub sources        │
│         ├── SAGA execution engine                               │
│         ├── TCC execution engine                                │
│         ├── Retry and compensation logic                        │
│         └── Enterprise persistence features                     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Installation Components

### 1. Python Layer

The Python layer provides:
- SAGA and TCC definition decorators (`@saga`, `@tcc`, `@saga_step`)
- Business logic execution in Python
- Type-safe data models with Pydantic
- Async/await support for modern Python

### 2. Java Subprocess Bridge

The Java bridge is automatically built during installation:
- **Source**: `fireflytx/java_bridge/` directory
- **Build Process**: Maven or javac + jar
- **Output**: `java-subprocess-bridge.jar` with all dependencies
- **Communication**: JSON files for Python-Java IPC

Build process checks:
1. Java availability (`java -version`)
2. Maven availability (`mvn -version`) - optional
3. Compiles bridge classes with Jackson dependencies
4. Creates shaded JAR for runtime execution

### 3. lib-transactional-engine Integration

The Java execution engine is set up automatically:
- **Source**: GitHub repository (firefly-oss/lib-transactional-engine)
- **Build**: Automatic Maven build from sources
- **Cache**: Local cache in `~/.fireflytx/build_cache/`
- **Features**: Full enterprise SAGA and TCC execution

## Verification

After installation, verify the setup:

```python
import asyncio
from fireflytx import SagaEngine
from fireflytx.decorators.saga import saga, saga_step
from fireflytx.core.saga_context import SagaContext

@saga(name="InstallationTest")
class InstallationTestSaga:
    @saga_step(step_id="test_step", retry=1, timeout_ms=5000)
    async def test_step(self, context: SagaContext, input_data: dict) -> dict:
        return {"status": "success", "message": "Installation verified!"}

async def verify_installation():
    async with SagaEngine() as engine:
        result = await engine.execute_by_class(
            InstallationTestSaga, 
            {"test": "data"}
        )
        
        if result.is_success:
            print("✅ Installation verified successfully!")
            print(f"   Engine used: {result.engine_used}")
            print(f"   Java version: {result.lib_transactional_version}")
        else:
            print("❌ Installation verification failed")
            print(f"   Error: {result.error}")

if __name__ == "__main__":
    asyncio.run(verify_installation())
```

## Installation Troubleshooting

### Java Not Found

If Java is not available during installation:

```
Warning: Java not found. Java bridge will be built at runtime if needed.
```

**Solution**: Install Java 11+ and re-run installation:

```bash
# macOS with Homebrew
brew install openjdk@17

# Ubuntu/Debian
sudo apt-get install openjdk-17-jdk

# Windows
# Download from https://adoptium.net/
```

### Maven Not Available

If Maven is not available:

```
Warning: Maven not found. Using javac directly.
```

This is normal - the build will fall back to javac + jar. For development, install Maven:

```bash
# macOS with Homebrew
brew install maven

# Ubuntu/Debian
sudo apt-get install maven

# Windows
# Download from https://maven.apache.org/
```

### Build Failures

If the Java bridge build fails during installation:

```
Warning: Java bridge build failed: <error details>
Bridge will be built automatically at runtime.
```

**What happens**: The system will automatically build the bridge on first use.

**Manual build** (optional):
```bash
cd fireflytx/java_bridge
./build.sh
```

### Runtime Bridge Building

If the bridge wasn't built during installation, it builds automatically:

```python
# First engine initialization triggers bridge build
engine = SagaEngine()
await engine.initialize()  # Bridge builds here if needed
```

## Platform-Specific Notes

### macOS (Apple Silicon)

The installation works seamlessly on Apple Silicon (M1/M2/M3):
- Uses subprocess bridge by default (no JPype1 compatibility issues)
- Java 17+ recommended for best performance
- Rosetta not required

### Windows

Windows installation notes:
- Ensure Java is in PATH
- PowerShell or Command Prompt both work
- WSL2 fully supported

### Linux

Linux installation is fully supported:
- All distributions with Java 11+ support
- Docker containers supported
- Alpine Linux requires `openjdk11-jre`

## Development Installation

For development work on the engine itself:

```bash
git clone https://github.com/firefly-oss/python-transactional-engine.git
cd python-transactional-engine

# Install in development mode
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install

# Run tests
python -m pytest tests/test_java_bridge.py -v
```

This installs additional development dependencies:
- pytest for testing
- black for code formatting  
- mypy for type checking
- pre-commit for Git hooks

## Docker Installation

For containerized deployments:

```dockerfile
FROM python:3.11-slim

# Install Java
RUN apt-get update && apt-get install -y openjdk-17-jre-headless && rm -rf /var/lib/apt/lists/*

# Install fireflytx
RUN pip install fireflytx

# Verify installation
RUN python -c "from fireflytx import SagaEngine; print('✅ Installation successful')"

COPY your_saga_app.py .
CMD ["python", "your_saga_app.py"]
```

## Performance Tuning

For production deployments, consider:

### JVM Heap Settings

The Java subprocess uses moderate heap by default. For high-throughput applications:

```python
# Custom JVM settings (if needed)
engine = SagaEngine()
# The bridge automatically manages JVM settings
```

### Connection Pooling

The subprocess bridge maintains persistent connections for efficiency:
- Automatic connection reuse
- Configurable timeouts
- Built-in error recovery

### Monitoring

Enable logging for production monitoring:

```python
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fireflytx")
```

## Next Steps

1. **Read the Architecture Guide**: See `PYTHON_DEFINES_JAVA_EXECUTES.md`
2. **Try Examples**: Check the `examples/` directory
3. **Run Tests**: Execute `python test_java_bridge.py`
4. **Build Your First SAGA**: Follow the quick start in README.md

## Support

If you encounter installation issues:

1. Check the troubleshooting section above
2. Review the GitHub issues for similar problems
3. Create a new issue with:
   - Operating system and version
   - Python version (`python --version`)
   - Java version (`java -version`)
   - Complete error output
   - Installation method used

The "Python defines, Java executes" architecture is designed to work out-of-the-box with minimal configuration while providing enterprise-grade transaction processing capabilities.