#!/bin/bash

# Build script for Java subprocess bridge
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BRIDGE_DIR="$SCRIPT_DIR"
TARGET_DIR="$BRIDGE_DIR/target"

echo "Building Java subprocess bridge..."

# Clean previous build
rm -rf "$TARGET_DIR"
mkdir -p "$TARGET_DIR/classes"

# Check if Java and Maven are available
if ! command -v javac &> /dev/null; then
    echo "Error: javac (Java compiler) not found. Please install JDK."
    exit 1
fi

if ! command -v mvn &> /dev/null; then
    echo "Warning: Maven not found. Using javac directly."
    USE_MAVEN=false
else
    USE_MAVEN=true
fi

if [ "$USE_MAVEN" = true ]; then
    # Build with Maven
    echo "Building with Maven..."
    cd "$BRIDGE_DIR"
    mvn clean package -DskipTests
    
    # Copy the built JAR to a known location
    if [ -f "$TARGET_DIR/java-subprocess-bridge-1.0.0-SNAPSHOT.jar" ]; then
        cp "$TARGET_DIR/java-subprocess-bridge-1.0.0-SNAPSHOT.jar" "$BRIDGE_DIR/java-subprocess-bridge.jar"
        echo "✅ Built Java subprocess bridge JAR: $BRIDGE_DIR/java-subprocess-bridge.jar"
    else
        echo "❌ Maven build failed - JAR not found"
        exit 1
    fi
else
    # Build with javac directly
    echo "Building with javac..."
    
    # Create temporary lib directory for Jackson JARs
    LIB_DIR="$TARGET_DIR/lib"
    mkdir -p "$LIB_DIR"
    
    # Download Jackson dependencies if they don't exist
    JACKSON_CORE="jackson-core-2.15.2.jar"
    JACKSON_DATABIND="jackson-databind-2.15.2.jar"
    JACKSON_ANNOTATIONS="jackson-annotations-2.15.2.jar"
    
    if [ ! -f "$LIB_DIR/$JACKSON_CORE" ]; then
        echo "Downloading Jackson Core..."
        curl -L "https://repo1.maven.org/maven2/com/fasterxml/jackson/core/jackson-core/2.15.2/$JACKSON_CORE" \
             -o "$LIB_DIR/$JACKSON_CORE"
    fi
    
    if [ ! -f "$LIB_DIR/$JACKSON_DATABIND" ]; then
        echo "Downloading Jackson Databind..."
        curl -L "https://repo1.maven.org/maven2/com/fasterxml/jackson/core/jackson-databind/2.15.2/$JACKSON_DATABIND" \
             -o "$LIB_DIR/$JACKSON_DATABIND"
    fi
    
    if [ ! -f "$LIB_DIR/$JACKSON_ANNOTATIONS" ]; then
        echo "Downloading Jackson Annotations..."
        curl -L "https://repo1.maven.org/maven2/com/fasterxml/jackson/core/jackson-annotations/2.15.2/$JACKSON_ANNOTATIONS" \
             -o "$LIB_DIR/$JACKSON_ANNOTATIONS"
    fi
    
    # Build classpath
    CLASSPATH="$LIB_DIR/$JACKSON_CORE:$LIB_DIR/$JACKSON_DATABIND:$LIB_DIR/$JACKSON_ANNOTATIONS"
    
    # Compile Java sources
    echo "Compiling Java sources..."
    find "$BRIDGE_DIR" -name "*.java" -not -path "*/target/*" | \
        xargs javac -cp "$CLASSPATH" -d "$TARGET_DIR/classes"
    
    # Create JAR
    echo "Creating JAR..."
    cd "$TARGET_DIR/classes"
    jar cfm "$BRIDGE_DIR/java-subprocess-bridge.jar" << EOF > "$TARGET_DIR/MANIFEST.MF"
Manifest-Version: 1.0
Main-Class: com.firefly.transactional.JavaSubprocessBridge
Class-Path: $(basename "$LIB_DIR"/$JACKSON_CORE) $(basename "$LIB_DIR"/$JACKSON_DATABIND) $(basename "$LIB_DIR"/$JACKSON_ANNOTATIONS)

EOF
    jar cfm "$BRIDGE_DIR/java-subprocess-bridge.jar" "$TARGET_DIR/MANIFEST.MF" .
    
    # Copy libraries
    cp "$LIB_DIR"/*.jar "$BRIDGE_DIR/"
    
    echo "✅ Built Java subprocess bridge JAR: $BRIDGE_DIR/java-subprocess-bridge.jar"
fi

echo "✅ Java subprocess bridge build complete"