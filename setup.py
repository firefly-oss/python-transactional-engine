#!/usr/bin/env python3
"""
Setup script for Firefly Transactional Engine Python Wrapper.
A Python wrapper for the Firefly lib-transactional-engine Java library.
"""

"""
Copyright (c) 2025 Firefly Software Solutions Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at:

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

from setuptools import setup, find_packages
from setuptools.command.install import install
from setuptools.command.develop import develop
import os
import subprocess
import sys
from pathlib import Path

# Read the contents of README file
this_directory = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

# Read version from __init__.py
def check_java_available():
    """Check if Java is available for building the bridge."""
    try:
        result = subprocess.run(['java', '-version'], capture_output=True, text=True)
        if result.returncode == 0:
            return True
    except FileNotFoundError:
        pass
    return False

def check_maven_available():
    """Check if Maven is available for building the bridge."""
    try:
        result = subprocess.run(['mvn', '-version'], capture_output=True, text=True)
        if result.returncode == 0:
            return True
    except FileNotFoundError:
        pass
    return False

def build_java_bridge():
    """Build the Java subprocess bridge during installation."""
    print("Building Java subprocess bridge...")
    
    # Check prerequisites
    if not check_java_available():
        print("Warning: Java not found. Java bridge will be built at runtime if needed.")
        return
    
    bridge_dir = Path(this_directory) / "fireflytx" / "java_bridge"
    if not bridge_dir.exists():
        print("Warning: Java bridge directory not found. Skipping bridge build.")
        return
    
    build_script = bridge_dir / "build.sh"
    if not build_script.exists():
        print("Warning: Java bridge build script not found. Skipping bridge build.")
        return
    
    try:
        # Make build script executable
        os.chmod(str(build_script), 0o755)
        
        # Run build script
        result = subprocess.run(
            ["bash", str(build_script)],
            cwd=str(bridge_dir),
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print("✅ Java subprocess bridge built successfully")
        else:
            print(f"Warning: Java bridge build failed: {result.stderr}")
            print("Bridge will be built automatically at runtime.")
            
    except Exception as e:
        print(f"Warning: Failed to build Java bridge: {e}")
        print("Bridge will be built automatically at runtime.")

class CustomInstallCommand(install):
    """Custom install command that builds the Java bridge."""
    
    def run(self):
        # Build Java bridge during installation
        build_java_bridge()
        
        # Run normal installation
        install.run(self)

class CustomDevelopCommand(develop):
    """Custom develop command that builds the Java bridge."""
    
    def run(self):
        # Build Java bridge during development installation
        build_java_bridge()
        
        # Run normal development installation  
        develop.run(self)

def get_version():
    import sys
    sys.path.insert(0, os.path.join(this_directory, 'fireflytx'))
    try:
        from fireflytx import __version__
        return __version__
    except ImportError:
        # Fallback version reading
        version = {}
        version_file = os.path.join(this_directory, 'fireflytx', '__init__.py')
        with open(version_file) as f:
            for line in f:
                if line.startswith('__version__'):
                    return line.split('=')[1].strip(' "\'\'\n')
        return '0.1.0'

setup(
    name='fireflytx',
    version=get_version(),
    author='Firefly OSS',
    author_email='dev@getfirefly.io',
    description='Python Wrapper for Firefly Transactional Engine - SAGA and TCC patterns',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/firefly-oss/python-transactional-engine',
    packages=find_packages(),
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Programming Language :: Python :: 3.13',
        'Programming Language :: Python :: 3.14',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: System :: Distributed Computing',
        'Topic :: Database :: Database Engines/Servers',
    ],
    python_requires='>=3.9',
    install_requires=[
        'JPype1>=1.5.0',
        'pydantic>=2.0.0',
        'typing-extensions>=4.0.0',
        'PyYAML>=6.0',
        'toml>=0.10.2',
        'dataclasses-json>=0.6.0',
    ],
    cmdclass={
        'install': CustomInstallCommand,
        'develop': CustomDevelopCommand,
    },
    extras_require={
        'dev': [
            'pytest>=7.0.0',
            'pytest-asyncio>=0.21.0',
            'pytest-cov>=4.0.0',
            'pytest-mock>=3.10.0',
            'pytest-xdist>=3.0.0',
            'black>=22.0.0',
            'ruff>=0.1.0',
            'mypy>=1.0.0',
            'isort>=5.12.0',
            'pre-commit>=3.0.0',
        ],
        'docs': [
            'sphinx>=5.0.0',
            'sphinx-rtd-theme>=1.2.0',
            'myst-parser>=1.0.0',
        ],
        'metrics': [
            'prometheus-client>=0.14.0',
        ],
        'logging': [
            'structlog>=22.0.0',
        ],
        'mqtt': [
            'asyncio-mqtt>=0.11.0',
        ],
        'kafka': [
            'aiokafka>=0.8.0',
        ],
        'redis': [
            'redis>=4.5.0',
            'aioredis>=2.0.0',
        ],
        'postgresql': [
            'asyncpg>=0.28.0',
            'psycopg2-binary>=2.9.0',
        ],
        'all': [
            'prometheus-client>=0.14.0',
            'structlog>=22.0.0',
            'asyncio-mqtt>=0.11.0',
            'aiokafka>=0.8.0',
            'redis>=4.5.0',
            'aioredis>=2.0.0',
            'asyncpg>=0.28.0',
            'psycopg2-binary>=2.9.0',
        ],
    },
    include_package_data=True,
    package_data={
        'fireflytx': [
            '*.jar', 'lib/*.jar',
            'java_bridge/*.jar',
            'java_bridge/*.java',
            'java_bridge/build.sh',
            'java_bridge/pom.xml',
            'java_bridge/src/**/*.java'
        ],
    },
    entry_points={
        'console_scripts': [
            'fireflytx=fireflytx.cli:main',
        ],
    },
    zip_safe=False,
)