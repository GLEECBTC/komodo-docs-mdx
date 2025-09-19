# 🧪 KDF Postman API Testing Infrastructure

This repository includes a comprehensive testing infrastructure for the Komodo DeFi Framework (KDF) API using Postman collections in Docker containers.

## 🎯 Overview

This testing infrastructure provides:

- **Automated KDF Testing**: Docker containers running different KDF configurations
- **Official Docker Integration**: Uses KDF's official Docker configurations for maximum compatibility
- **Branch Flexibility**: Test any KDF branch, tag, or commit from the official repository
- **Environment Matrix**: Support for HD and Iguana wallet types with Native TCP/SSL protocols
- **CI/CD Integration**: GitHub Actions workflow for automated testing
- **Response Collection**: Structured collection and formatting of API responses
- **Local Development**: Scripts for local testing and debugging

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose
- Git (for cloning)

### Run Tests Locally

```bash
# Test with default dev branch
./utils/scripts/test_setup.sh all

# Test with main branch
KDF_BRANCH=dev ./utils/scripts/test_setup.sh all

# Test specific feature branch
KDF_BRANCH=feature/new-api ./utils/scripts/test_setup.sh all
```

### Manual Docker Compose

```bash
# Set the KDF branch (optional, defaults to 'dev')
export KDF_BRANCH=dev

# Start all services
docker compose up --build

# Start only specific services
docker compose up --build kdf-native-hd
```

### GitHub Actions

1. Go to **Actions** tab
2. Select **"KDF Postman API Tests"** workflow  
3. Click **"Run workflow"**
4. Choose:
   - **Environment**: `all`, `native_hd`, or `native_iguana`
   - **KDF Branch**: Any valid branch/tag/commit from KDF repository

## 📁 File Structure

```
├── docker-compose.yml                          # Main orchestration
├── .github/workflows/postman-kdf-tests.yml     # CI/CD workflow
├── postman/
│   ├── generated/                              # Auto-generated collections
│   └── reports/                                # Test result reports
├── utils/
│   ├── docker/
│   │   ├── build-kdf.sh                        # Official KDF Docker build script
│   │   ├── Dockerfile.processor                # Response processor
│   │   ├── kdf-config*/                        # Environment configs
│   │   └── kdf-db*/                            # Database volumes
│   └── scripts/
│       ├── test_setup.sh                       # Local test script
│       ├── process_responses.py                # Response processor
│       └── validate_postman.py                 # Collection validator
└── src/data/responses/kdf/                     # Response templates
```

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    GitHub Actions                       │
│  Triggers: Push/PR/Manual with branch selection        │
└─────────────────────┬───────────────────────────────────┘
                      │
    ┌─────────────────▼─────────────────┐
    │          Build Process            │
    │                                   │
    │  ┌─────────────────────────────┐  │
    │  │     Clone KDF Repository    │  │
    │  │   (Official Docker Setup)   │  │
    │  └─────────────┬───────────────┘  │
    │                │                  │
    │  ┌─────────────▼───────────────┐  │
    │  │   Use Official Dockerfile   │  │
    │  │   (.docker/Dockerfile.*)    │  │
    │  └─────────────┬───────────────┘  │
    └────────────────┼───────────────────┘
                     │
    ┌────────────────▼───────────────────┐
    │          Docker Host              │
    │                                   │
    │  ┌─────────────┬─────────────┐    │
    │  │ KDF Native  │ KDF Native  │    │
    │  │ HD Wallet   │ Iguana      │    │
    │  │ (Port 7783) │ (Port 7784) │    │
    │  └─────────────┴─────────────┘    │
    │            │         │            │
    │  ┌─────────────┬─────────────┐    │
    │  │   Newman    │   Newman    │    │
    │  │  HD Tests   │ Iguana Tests│    │
    │  └─────────────┴─────────────┘    │
    │            │         │            │
    │  ┌─────────────────────────────┐  │
    │  │    Response Processor       │  │
    │  │   (Consolidates Results)    │  │
    │  └─────────────────────────────┘  │
    └───────────────────────────────────┘
                      │
    ┌─────────────────▼─────────────────┐
    │        Artifact Storage           │
    │  • Test Reports (JSON/XML)        │
    │  • Response Collections           │
    │  • Container Logs                 │
    └───────────────────────────────────┘
```

### 🔧 Official Docker Integration

The testing infrastructure leverages the [official KDF Docker configurations](https://github.com/KomodoPlatform/komodo-defi-framework/tree/main/.docker) to ensure consistency and reliability with the official KDF development environment.

#### Integration Approach

**1. Dynamic Repository Cloning**
```bash
# The build script clones the specified KDF branch
git clone --depth 1 --branch ${KDF_BRANCH} \
    https://github.com/KomodoPlatform/komodo-defi-framework.git
```

**2. Official Dockerfile Detection**
```bash
# Priority order for Dockerfile selection:
1. .docker/Dockerfile.release     # Production builds (preferred)
2. .docker/Dockerfile             # Default build
# Fails if no official Dockerfile is found
```

**3. Seamless Integration**
- Uses official build configurations and dependencies
- Inherits any improvements made by the KDF team
- Maintains compatibility with official runtime environment

#### Key Benefits

**Consistency**
- Uses the exact same build process as official KDF
- Inherits official dependency versions and configurations
- Reduces environment-specific issues

**Maintenance**
- Automatically gets updates when KDF team improves Docker setup
- No need to manually sync build configurations
- Future-proof against KDF infrastructure changes

**Reliability**
- Tested configurations from the KDF development team
- Official runtime environment compatibility
- Reduced custom configuration complexity

**Quality Assurance**
- Can test any branch, tag, or commit
- Enforces use of official build configurations
- Immediate feedback if official setup has issues

#### Comparison: Before vs After

| Aspect | Before (Custom) | After (Official) |
|--------|----------------|------------------|
| **Build Config** | Manual maintenance | Auto-sync with KDF team |
| **Dependencies** | Custom specification | Official versions |
| **Updates** | Manual tracking | Automatic with branch |
| **Reliability** | Potential drift | Tested configurations |
| **Maintenance** | High effort | Minimal effort |
| **Compatibility** | Risk of issues | Guaranteed compatibility |

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `KDF_BRANCH` | KDF repository branch to test | `dev` |
| `RUST_LOG` | Rust logging level | `info` |
| `KDF_BASE_URL` | Base URL for KDF instance | Auto-detected |
| `WALLET_TYPE` | Wallet type (`hd` or `iguana`) | Environment-specific |
| `ENVIRONMENT` | Environment name (`native_hd`, `native_iguana`) | Auto-set |

### Supported Environments

| Environment | Wallet Type | Description |
|-------------|-------------|-------------|
| `native_hd` | HD | Native with Hierarchical Deterministic wallets |
| `native_iguana` | Iguana | Native with legacy Iguana wallets |

*Note: WASM environments and hardware wallet support planned for future releases.*

## 📊 Output

### Test Reports

- **Newman JSON/XML**: Detailed test execution results
- **JUnit XML**: GitHub Actions test integration
- **Response Collections**: Structured API response data

### Response Format

Results follow the existing `coin_activation.json` structure with additional metadata:

```json
{
  "MethodName": {
    "success": [
      {
        "title": "Test Case Name",
        "notes": "Environment: native_hd, Wallet: hd", 
        "json": { /* API response */ },
        "metadata": {
          "environment": "native_hd",
          "wallet_type": "hd",
          "timestamp": "2025-01-27T10:30:00Z",
          "method": "task::enable_eth::init",
          "status_code": 200,
          "response_time": 1234,
          "test_passed": true
        }
      }
    ],
    "error": [ /* Error responses */ ]
  }
}
```

## 🔧 Technical Details

### Build Process Flow
```
1. Clone KDF repository (specified branch)
2. Detect available Dockerfiles in .docker/
3. Use official Dockerfile if available
4. Build with official configurations
5. Tag as kdf:latest for Docker Compose
6. Clean up temporary build context
```

### File Hierarchy
```
/tmp/kdf-build/                    # Temporary build context
├── .docker/
│   ├── Dockerfile.release         # Official production build
│   ├── Dockerfile                 # Official development build
│   └── ...                        # Other official configs
├── Cargo.toml                     # Project configuration
├── rust-toolchain.toml            # Rust toolchain specification
└── ...                            # Full KDF source code
```

### Docker Services

#### KDF Instances

- **`kdf-native-hd`**: HD wallet KDF instance (port 7783)
- **`kdf-native-nonhd`**: Iguana wallet KDF instance (port 7784)

Both instances include:
- Health checks for startup validation
- Volume mounts for configuration and database persistence
- Network isolation within `kdf-network`

#### Test Runners

- **`newman-native-hd`**: Runs Postman tests against HD environment
- **`newman-native-nonhd`**: Runs Postman tests against Iguana environment

#### Response Processing

- **`response-processor`**: Consolidates Newman reports into structured response format

### Docker Compose Overrides

For custom configurations, create a `docker-compose.override.yml`:

```yaml
version: '3.8'
services:
  kdf-native-hd:
    environment:
      - RUST_LOG=debug  # More verbose logging
    ports:
      - "7785:7783"     # Different port mapping
```

## 🐛 Troubleshooting

### Build Script Issues
```bash
# Enable debug mode
DEBUG=1 KDF_BRANCH=dev ./utils/docker/build-kdf.sh

# Manual verification
ls -la /tmp/kdf-build/.docker/

# Check available Dockerfiles
find /tmp/kdf-build -name "Dockerfile*"
```

### Build Failure Scenarios
The system will fail with clear error messages when:
- No official Dockerfile found in `.docker/` directory
- Official Dockerfile build fails
- Network issues prevent repository cloning

### Common Issues

**1. Health check failures**:
```bash
# Check KDF logs
docker compose logs kdf-native-hd
docker compose logs kdf-native-nonhd
```

**2. Newman test failures**:
```bash
# Check Newman logs
docker compose logs newman-native-hd
```

**3. Port conflicts**:
- Ensure ports 7783-7784 are available
- Modify port mappings in docker-compose.yml if needed

**4. Volume permission issues**:
```bash
# Fix permissions
sudo chown -R $USER:$USER utils/docker/kdf-db*
```

**5. Branch not found**: Verify branch exists in KDF repository
**6. Build failures**: Check Docker logs and official KDF requirements
**7. Permission issues**: Ensure build script is executable

### Debug Mode

For detailed debugging:

```bash
# Start with debug logging
RUST_LOG=debug docker compose up kdf-native-hd

# Run Newman with verbose output
docker compose run --rm newman-native-hd \
  newman run /postman/kdf_postman_collection.json \
  --environment /postman/environments/kdf_native_hd_collection.json \
  --verbose
```

### Clean Start
```bash
# Clean up previous runs (KDF-related only, safe)
./utils/scripts/test_setup.sh clean

# Deep clean all Docker resources (system-wide, with confirmation)
./utils/scripts/test_setup.sh deep-clean

# Full restart
docker compose down -v
./utils/scripts/test_setup.sh all
```

## 🔮 Future Enhancements

- **Cache optimization**: Reuse cloned repositories for faster builds
- **Multi-arch support**: Leverage official multi-architecture builds
- **CI/CD integration**: Official Docker registry integration
- **Version pinning**: Lock to specific KDF commits for stability
- **WASM Environment Support**: WebAssembly-based KDF testing
- **Hardware Wallet Integration**: Trezor/Ledger automation  
- **Performance Benchmarking**: Response time tracking
- **Parallel Testing**: Multiple concurrent test runs
- **Custom Test Filtering**: Environment-specific test suites
- **Slack/Discord Integration**: Test result notifications

## 🤝 Contributing

When adding new test scenarios:

1. **Adding New Tests**: Update Postman collections in `postman/generated/`
2. **New Environments**: Add configurations in `utils/docker/kdf-config-*`
3. **Response Templates**: Update `src/data/responses/kdf/`
4. **Local Testing**: Always test with `./utils/scripts/test_setup.sh` before pushing

## 📚 Related Documentation

- [KDF API Documentation](src/pages/komodo-defi-framework/)
- [Docker Configuration](utils/docker/)
- [KDF Official Docker Setup](https://github.com/KomodoPlatform/komodo-defi-framework/tree/main/.docker)

## 🆘 Support

For issues or questions:
- Create an issue in this repository
- Check existing [KDF documentation](https://developers.komodoplatform.com/)
- Review container logs for debugging information

---

This integration ensures our testing infrastructure stays aligned with the official KDF development process while maintaining the flexibility to test any branch or configuration.

**Built with ❤️ for the Komodo DeFi Framework community**
