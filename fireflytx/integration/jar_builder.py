"""
JAR downloader and builder for lib-transactional-engine.

This module handles downloading the source code from GitHub and building the JAR file.
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

import hashlib
import logging
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class JarBuilder:
    """Builds the lib-transactional-engine JAR from GitHub sources."""

    DEFAULT_REPO_URL = "https://github.com/firefly-oss/lib-transactional-engine.git"
    DEFAULT_BRANCH = "main"

    def __init__(
        self,
        repo_url: str = DEFAULT_REPO_URL,
        branch: str = DEFAULT_BRANCH,
        build_cache_dir: Optional[Path] = None,
    ):
        """
        Initialize the JAR builder.

        Args:
            repo_url: GitHub repository URL
            branch: Git branch to build from
            build_cache_dir: Directory to cache built JARs
        """
        self.repo_url = repo_url
        self.branch = branch
        self.build_cache_dir = build_cache_dir or Path.home() / ".fireflytx" / "build_cache"
        self.build_cache_dir.mkdir(parents=True, exist_ok=True)

    def get_jar_path(self, force_rebuild: bool = False) -> Path:
        """
        Get the path to the built JAR file, building it if necessary.

        Args:
            force_rebuild: Force rebuilding even if cached JAR exists

        Returns:
            Path to the built JAR file

        Raises:
            RuntimeError: If build fails
        """
        # Check for cached JAR
        cached_jar = self._get_cached_jar_path()
        if cached_jar.exists() and not force_rebuild:
            logger.info(f"Using cached JAR: {cached_jar}")
            return cached_jar

        logger.info("Building JAR from GitHub sources...")
        return self._build_jar()

    def _get_cached_jar_path(self) -> Path:
        """Get the path where the cached JAR should be."""
        # Create a hash of repo_url + branch for cache key
        cache_key = hashlib.md5(f"{self.repo_url}#{self.branch}".encode()).hexdigest()[:8]
        return self.build_cache_dir / f"lib-transactional-engine-{cache_key}.jar"

    def _build_jar(self) -> Path:
        """Build the JAR from source code."""
        with tempfile.TemporaryDirectory(prefix="transactional_build_") as temp_dir:
            temp_path = Path(temp_dir)
            repo_dir = temp_path / "repo"

            try:
                # Clone the repository
                logger.info(f"Cloning {self.repo_url} (branch: {self.branch})")
                subprocess.run(
                    [
                        "git",
                        "clone",
                        "--branch",
                        self.branch,
                        "--depth",
                        "1",  # Shallow clone for faster download
                        self.repo_url,
                        str(repo_dir),
                    ],
                    check=True,
                    capture_output=True,
                )

                # Check if Maven wrapper exists
                mvnw_path = repo_dir / "mvnw"
                if mvnw_path.exists():
                    maven_cmd = ["./mvnw"]
                    # Make it executable
                    mvnw_path.chmod(0o755)
                else:
                    # Fallback to system Maven
                    maven_cmd = ["mvn"]

                # Build the project
                logger.info("Building project with Maven...")
                subprocess.run(
                    [*maven_cmd, "clean", "package", "-DskipTests"],
                    cwd=repo_dir,
                    check=True,
                    capture_output=True,
                )

                # Find the built JAR file
                target_dir = repo_dir / "target"
                jar_files = list(target_dir.glob("*.jar"))

                # Filter out sources and javadoc jars
                jar_files = [
                    jar
                    for jar in jar_files
                    if not any(suffix in jar.name for suffix in ["-sources", "-javadoc", "-tests"])
                ]

                if not jar_files:
                    raise RuntimeError("No JAR file found in target directory")

                # Use the first (and hopefully only) JAR file
                built_jar = jar_files[0]
                logger.info(f"Found built JAR: {built_jar.name}")

                # Copy to cache
                cached_jar = self._get_cached_jar_path()
                shutil.copy2(built_jar, cached_jar)
                logger.info(f"JAR cached at: {cached_jar}")

                return cached_jar

            except subprocess.CalledProcessError as e:
                error_msg = f"Build failed: {e}"
                if e.stdout:
                    error_msg += f"\nStdout: {e.stdout.decode()}"
                if e.stderr:
                    error_msg += f"\nStderr: {e.stderr.decode()}"
                logger.error(error_msg)
                raise RuntimeError(error_msg)

            except Exception as e:
                logger.error(f"Unexpected error during build: {e}")
                raise RuntimeError(f"Build failed: {e}")

    def check_prerequisites(self) -> Dict[str, bool]:
        """
        Check if build prerequisites are available.

        Returns:
            Dict with prerequisite status
        """
        prerequisites = {}

        # Check for Git
        try:
            subprocess.run(["git", "--version"], check=True, capture_output=True)
            prerequisites["git"] = True
        except (subprocess.CalledProcessError, FileNotFoundError):
            prerequisites["git"] = False

        # Check for Java
        try:
            result = subprocess.run(
                ["java", "-version"], check=True, capture_output=True, text=True
            )
            prerequisites["java"] = True
            # Extract Java version
            version_line = result.stderr.split("\n")[0] if result.stderr else ""
            prerequisites["java_version"] = version_line
        except (subprocess.CalledProcessError, FileNotFoundError):
            prerequisites["java"] = False
            prerequisites["java_version"] = "Not found"

        # Check for Maven (optional - will use mvnw if available)
        try:
            subprocess.run(["mvn", "--version"], check=True, capture_output=True)
            prerequisites["maven"] = True
        except (subprocess.CalledProcessError, FileNotFoundError):
            prerequisites["maven"] = False

        return prerequisites

    def clear_cache(self) -> None:
        """Clear the build cache."""
        if self.build_cache_dir.exists():
            shutil.rmtree(self.build_cache_dir)
            self.build_cache_dir.mkdir(parents=True, exist_ok=True)
            logger.info("Build cache cleared")


def get_jar_path(
    force_rebuild: bool = False, repo_url: Optional[str] = None, branch: Optional[str] = None
) -> Path:
    """
    Convenience function to get the JAR path.

    Args:
        force_rebuild: Force rebuilding even if cached
        repo_url: Custom repository URL
        branch: Custom branch name

    Returns:
        Path to the JAR file
    """
    builder_args = {}
    if repo_url:
        builder_args["repo_url"] = repo_url
    if branch:
        builder_args["branch"] = branch

    builder = JarBuilder(**builder_args)
    return builder.get_jar_path(force_rebuild=force_rebuild)


def check_build_environment() -> bool:
    """
    Check if the build environment is ready.

    Returns:
        True if environment is ready, False otherwise
    """
    builder = JarBuilder()
    prereqs = builder.check_prerequisites()

    missing = [
        name for name, available in prereqs.items() if name in ["git", "java"] and not available
    ]

    if missing:
        logger.error(f"Missing prerequisites: {', '.join(missing)}")
        logger.info("Please install:")
        if "git" in missing:
            logger.info("- Git: https://git-scm.com/downloads")
        if "java" in missing:
            logger.info("- Java 11+: https://adoptium.net/")
        return False

    logger.info("Build environment is ready")
    logger.info(f"Java version: {prereqs.get('java_version', 'Unknown')}")
    logger.info(f"Maven available: {prereqs.get('maven', False)}")

    return True
