"""
Automatic dependency installer for fireflytx.

This module handles downloading and setting up all required Java dependencies
during package installation.

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

import logging
import os
import subprocess
import tempfile
import urllib.request
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class DependencyInstaller:
    """Handles automatic installation of Java dependencies."""

    def __init__(self, target_dir: Optional[Path] = None):
        """Initialize the dependency installer."""
        self.target_dir = target_dir or Path(__file__).parent.parent / "deps"
        self.target_dir.mkdir(parents=True, exist_ok=True)

    def install_dependencies(self, force_reinstall: bool = False) -> bool:
        """
        Install all required Java dependencies.

        Args:
            force_reinstall: Force reinstallation even if dependencies exist

        Returns:
            True if installation successful, False otherwise
        """
        try:
            # Check if dependencies already exist
            if not force_reinstall and self._dependencies_exist():
                logger.info("Dependencies already installed")
                return True

            logger.info("Installing Java dependencies for lib-transactional-engine...")

            # Method 1: Try to download from Maven source
            if self._install_from_maven_source():
                logger.info("Successfully installed dependencies from Maven source")
                return True

            # Method 2: Fallback to individual dependency download
            logger.warning("Maven source install failed, falling back to individual downloads")
            return self._install_individual_dependencies()

        except Exception as e:
            logger.error(f"Failed to install dependencies: {e}")
            return False

    def _dependencies_exist(self) -> bool:
        """Check if dependencies are already installed."""
        if not self.target_dir.exists():
            return False

        jar_files = list(self.target_dir.glob("*.jar"))
        return len(jar_files) >= 50  # Expect at least 50 dependencies

    def _install_from_maven_source(self) -> bool:
        """Install dependencies by building from Maven source."""
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                repo_dir = temp_path / "lib-transactional-engine"

                # Clone the repository
                logger.info("Cloning lib-transactional-engine repository...")
                subprocess.run(
                    [
                        "git",
                        "clone",
                        "--depth",
                        "1",
                        "https://github.com/firefly-oss/lib-transactional-engine.git",
                        str(repo_dir),
                    ],
                    check=True,
                    capture_output=True,
                )

                # Download dependencies using Maven
                logger.info("Downloading dependencies using Maven...")
                subprocess.run(
                    [
                        "mvn",
                        "dependency:copy-dependencies",
                        "-DoutputDirectory=" + str(self.target_dir),
                        "-DincludeScope=runtime",
                    ],
                    cwd=repo_dir,
                    check=True,
                    capture_output=True,
                )

                jar_count = len(list(self.target_dir.glob("*.jar")))
                logger.info(f"Downloaded {jar_count} dependency JARs")

                return jar_count > 0

        except subprocess.CalledProcessError as e:
            logger.warning(f"Maven dependency download failed: {e}")
            return False
        except Exception as e:
            logger.warning(f"Source installation failed: {e}")
            return False

    def _install_individual_dependencies(self) -> bool:
        """Install critical dependencies individually."""
        critical_dependencies = [
            {
                "name": "slf4j-api-2.0.9.jar",
                "url": "https://repo1.maven.org/maven2/org/slf4j/slf4j-api/2.0.9/slf4j-api-2.0.9.jar",
            },
            {
                "name": "slf4j-simple-2.0.9.jar",
                "url": "https://repo1.maven.org/maven2/org/slf4j/slf4j-simple/2.0.9/slf4j-simple-2.0.9.jar",
            },
            {
                "name": "jackson-core-2.15.2.jar",
                "url": "https://repo1.maven.org/maven2/com/fasterxml/jackson/core/jackson-core/2.15.2/jackson-core-2.15.2.jar",
            },
            {
                "name": "jackson-databind-2.15.2.jar",
                "url": "https://repo1.maven.org/maven2/com/fasterxml/jackson/core/jackson-databind/2.15.2/jackson-databind-2.15.2.jar",
            },
            {
                "name": "jackson-annotations-2.15.2.jar",
                "url": "https://repo1.maven.org/maven2/com/fasterxml/jackson/core/jackson-annotations/2.15.2/jackson-annotations-2.15.2.jar",
            },
        ]

        success_count = 0
        for dep in critical_dependencies:
            try:
                target_path = self.target_dir / dep["name"]
                if target_path.exists():
                    logger.debug(f"Dependency {dep['name']} already exists")
                    success_count += 1
                    continue

                logger.info(f"Downloading {dep['name']}...")
                urllib.request.urlretrieve(dep["url"], target_path)
                success_count += 1

            except Exception as e:
                logger.warning(f"Failed to download {dep['name']}: {e}")

        logger.info(
            f"Downloaded {success_count}/{len(critical_dependencies)} critical dependencies"
        )
        return success_count >= len(critical_dependencies) // 2  # At least half successful

    def verify_installation(self) -> bool:
        """Verify that the installation is working correctly."""
        try:
            from ..integration.bridge import JavaSubprocessBridge

            # Try to start the bridge with dependencies
            bridge = JavaSubprocessBridge()
            bridge.start_jvm()

            if bridge.is_jvm_started():
                logger.info("Installation verification successful")
                bridge.shutdown()
                return True
            else:
                logger.error("Installation verification failed - bridge could not start")
                return False

        except Exception as e:
            logger.error(f"Installation verification failed: {e}")
            return False


def install_dependencies_if_needed(force_reinstall: bool = False) -> bool:
    """
    Install dependencies if they don't exist or if forced.

    This function is called during package import to ensure dependencies are available.
    """
    try:
        installer = DependencyInstaller()
        return installer.install_dependencies(force_reinstall)
    except Exception as e:
        logger.warning(f"Could not install dependencies automatically: {e}")
        return False


# Auto-install on module import
if os.environ.get("FIREFLYTX_SKIP_AUTO_INSTALL", "").lower() not in ("1", "true", "yes"):
    try:
        install_dependencies_if_needed()
    except Exception:
        # Don't fail package import if dependency installation fails
        pass
