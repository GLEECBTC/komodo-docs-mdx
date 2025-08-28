#!/bin/bash
#
# KDF Docker Build Script - Using Multi-Stage Docker Build
# This approach uses proper Docker multi-stage builds to avoid cross-device link issues
# while following all official KDF patterns from their GitHub Actions workflows.
#

set -e

# Default values (matching official workflows)
KDF_BRANCH="${KDF_BRANCH:-dev}"
IMAGE_TAG="${IMAGE_TAG:-kdf:latest}"
BUILD_CONTEXT="${BUILD_CONTEXT:-tmp/kdf-build}"

echo "🔨 KDF Multi-Stage Docker Build using official CI patterns"
echo "   Branch: $KDF_BRANCH"
echo "   Tag: $IMAGE_TAG"
echo "   Build context: $BUILD_CONTEXT"

# Step 1: Clean up existing build context with proper permissions
echo "🧹 Cleaning up existing build context..."
if [ -d "$BUILD_CONTEXT" ]; then
    # Use docker to clean up files created by previous container runs (as root)
    docker run --rm \
        -v "$(pwd)/$BUILD_CONTEXT":/cleanup \
        --user root \
        debian:bullseye-slim \
        bash -c "rm -rf /cleanup/* /cleanup/.* 2>/dev/null || true" || true
    
    # Clean up the directory structure
    rm -rf "$BUILD_CONTEXT" 2>/dev/null || sudo rm -rf "$BUILD_CONTEXT" || true
fi

mkdir -p "$BUILD_CONTEXT"

# Step 2: Clone the KDF repository
echo "📥 Cloning KDF repository (branch: $KDF_BRANCH)..."
git clone --depth 1 --branch "$KDF_BRANCH" \
    https://github.com/KomodoPlatform/komodo-defi-framework.git \
    "$BUILD_CONTEXT"

# Step 3: Build the build container
cd "$BUILD_CONTEXT"
docker build -t kdf-build-container -f .docker/Dockerfile.ci-container .

# Step 4: Install protoc and build KDF (combined to persist dependencies)
echo "📦 Installing protoc v25.3 and building KDF..."
docker run -v "$(pwd)":/app -w /app kdf-build-container bash -c '
    # Download protoc v25.3 (matching the official workflow)
    echo "Downloading protoc v25.3..."
    wget -q https://github.com/protocolbuffers/protobuf/releases/download/v25.3/protoc-25.3-linux-x86_64.zip
    
    # Verify checksum (matching the official workflow)
    echo "Verifying checksum..."
    echo "f853e691868d0557425ea290bf7ba6384eef2fa9b04c323afab49a770ba9da80  protoc-25.3-linux-x86_64.zip" | sha256sum -c
    
    # Install protoc
    echo "Installing protoc..."
    unzip -q protoc-25.3-linux-x86_64.zip -d /tmp/protobuf
    cp /tmp/protobuf/bin/protoc /usr/local/bin/
    chmod +x /usr/local/bin/protoc
    
    # Verify installation
    echo "Verifying protoc installation..."
    protoc --version
    
    # Clean up download files
    rm -rf protoc-25.3-linux-x86_64.zip /tmp/protobuf
    
    # Set KDF_BUILD_TAG using git commit hash
    echo "Setting KDF_BUILD_TAG..."
    export KDF_BUILD_TAG=$(git rev-parse --short=7 HEAD)
    echo "KDF_BUILD_TAG: $KDF_BUILD_TAG"
    
    # Now build KDF with protoc available (release mode for Dockerfile.release)
    echo "Building KDF in release mode with protoc available..."
    export PATH="/usr/local/bin:$PATH"
    cargo build --release
'


# Step 5: Build the final Docker image with the compiled binary
echo "🐳 Building final Docker image..."
docker build -t "$IMAGE_TAG" -f .docker/Dockerfile.release .

# Cleanup
cd ..
echo ""
echo "✅ Successfully built KDF Docker image: $IMAGE_TAG"
echo "🧹 Build context preserved at: $BUILD_CONTEXT"
echo "   To remove it: rm -rf $BUILD_CONTEXT"