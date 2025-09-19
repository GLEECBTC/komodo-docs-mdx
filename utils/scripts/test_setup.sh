#!/bin/bash
#
# Local test script for KDF Postman testing setup.
# This script allows you to test the Docker setup locally before running in CI.
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check dependencies
check_dependencies() {
    print_status "Checking dependencies..."
    
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed or not in PATH"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        print_error "Docker Compose is not installed"
        exit 1
    fi
    
    print_status "Dependencies check passed"
}

# Clean up any existing containers
cleanup() {
    print_status "Cleaning up existing containers..."
    docker compose down -v 2>/dev/null || true
    
    # Clean up only our specific images and networks
    print_status "Cleaning up KDF-related Docker resources..."
    docker image rm kdf:latest 2>/dev/null || true
    docker image rm response-processor:latest 2>/dev/null || true
    docker network rm komodo-docs-mdx_kdf-network 2>/dev/null || true
    
    # Clean up dangling images from our builds only (safer than system prune)
    docker image prune -f --filter "dangling=true" 2>/dev/null || true
}

# Build and start services
start_services() {
    local kdf_branch="${KDF_BRANCH:-dev}"
    print_status "Building and starting KDF services (branch: $kdf_branch)..."
    
    # Create test reports directory
    mkdir -p test-reports
    chmod 777 test-reports
    
    # Export KDF_BRANCH for docker compose
    export KDF_BRANCH="$kdf_branch"
    
    # Build KDF image using official setup
    print_status "Building KDF image from official repository..."
    ./utils/docker/build-kdf.sh
    
    # Start only the KDF instances first (no --build needed as image is pre-built)
    docker compose up -d kdf-native-hd kdf-native-nonhd
    
    print_status "Waiting for services to be healthy..."
    local max_wait=300
    local wait_time=0
    
    while [ $wait_time -lt $max_wait ]; do
        if docker compose ps | grep -E "(kdf-native-hd|kdf-native-nonhd)" | grep -q "healthy"; then
            print_status "Services are healthy!"
            return 0
        fi
        
        sleep 10
        wait_time=$((wait_time + 10))
        docker compose logs kdf-native-hd --tail=50
        docker compose logs kdf-native-nonhd --tail=50
        print_status "Still waiting... ($wait_time/$max_wait seconds)"
    done
    
    print_error "Services failed to become healthy within timeout"
    docker compose logs kdf-native-hd
    docker compose logs kdf-native-nonhd
    return 1
}

# Run tests
run_tests() {
    print_status "Running Postman tests..."
    
    # Run tests for both environments
    print_status "Running Native HD tests..."
    docker compose up --no-deps newman-native-hd || print_warning "Native HD tests had issues"
    
    print_status "Running Native Iguana tests..."
    docker compose up --no-deps newman-native-nonhd || print_warning "Native Iguana tests had issues"
    
    print_status "Processing test results..."
    docker compose up --no-deps response-processor || print_warning "Response processing had issues"
}

# Show results
show_results() {
    print_status "Test Results Summary:"
    
    echo ""
    echo "=== Generated test reports ==="
    find test-reports -type f -ls 2>/dev/null || echo "No test reports found"
    
    echo ""
    echo "=== Generated response reports ==="
    find postman/reports -type f -name "*.json" -ls 2>/dev/null || echo "No response reports found"
    
    echo ""
    echo "=== Container logs ==="
    echo "KDF Native HD logs:"
    docker compose logs --tail=10 kdf-native-hd
    
    echo ""
    echo "KDF Native Non-HD logs:"
    docker compose logs --tail=10 kdf-native-nonhd
}

# Main function
main() {
    print_status "Starting KDF Postman Test Setup"
    
    # Parse command line arguments
    case "${1:-all}" in
        "clean")
            cleanup
            exit 0
            ;;
        "deep-clean")
            print_warning "This will remove all unused Docker resources system-wide!"
            read -p "Are you sure? (y/N): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                cleanup
                print_status "Performing deep clean..."
                docker system prune -f
            else
                print_status "Deep clean cancelled"
            fi
            exit 0
            ;;
        "build")
            check_dependencies
            start_services
            ;;
        "test")
            run_tests
            show_results
            ;;
        "all")
            check_dependencies
            cleanup
            start_services
            run_tests
            show_results
            ;;
        *)
            echo "Usage: $0 [clean|deep-clean|build|test|all]"
            echo "  clean: Clean up KDF-related containers and images only"
            echo "  deep-clean: Clean up all unused Docker resources (system-wide, with confirmation)"
            echo "  build: Build and start KDF services"
            echo "  test: Run tests (assumes services are running)"
            echo "  all: Full workflow (default)"
            echo ""
            echo "Environment variables:"
            echo "  KDF_BRANCH: KDF repository branch to build (default: dev)"
            echo ""
            echo "Examples:"
            echo "  $0 clean                    # Safe cleanup of only KDF resources"
            echo "  $0 deep-clean               # System-wide cleanup (with confirmation)"
            echo "  KDF_BRANCH=dev $0 all       # Test dev branch"
            exit 1
            ;;
    esac
    
    print_status "KDF Postman test setup completed!"
}

# Trap to cleanup on exit
trap cleanup EXIT

# Run main function
main "$@"
