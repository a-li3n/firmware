# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Meshtastic is an open-source LoRa mesh networking project for long-range, low-power communication without internet or cellular infrastructure. The firmware enables text messaging, location sharing, and telemetry over a decentralized mesh network.

### Supported Platforms
- **ESP32** (ESP32, ESP32-S3, ESP32-C3, ESP32-C6, ESP32-S2) - Most common
- **nRF52** (nRF52840, nRF52833) - Low power Nordic chips
- **RP2040/RP2350** - Raspberry Pi Pico variants
- **STM32WL** - STM32 with integrated LoRa
- **Linux/Portduino** - Native Linux builds (Raspberry Pi, etc.)

### Supported Radio Chips
- **SX1262/SX1268** - Sub-GHz LoRa (868/915 MHz)
- **SX1280** - 2.4 GHz LoRa
- **LR1110/LR1120/LR1121** - Wideband radios
- **RF95** - Legacy RFM95 modules
- **LLCC68** - Low-cost LoRa

## Build System

### Build Commands

The project uses **PlatformIO**. Common commands:

```bash
# Build specific hardware target
pio run -e tbeam
pio run -e heltec-v3

# Build and upload to device
pio run -e tbeam -t upload

# Build native/Linux version
pio run -e native
# or
./bin/build-native.sh

# Build platform-specific (ESP32, nRF52, etc.)
./bin/build-esp32.sh <environment>
./bin/build-nrf52.sh <environment>
./bin/build-rp2xx0.sh <environment>

# Run tests (native platform only)
pio test -e native

# Run tests with coverage
pio test -e coverage
platformio test -e coverage -v --junit-output-path testreport.xml

# Integration tests with simulator
.pio/build/coverage/program &  # Start simulator
python3 -c 'from meshtastic.test import testSimulator; testSimulator()'
./bin/test-simulator.sh        # End-to-end simulator test

# List all available board targets
pio project data | grep env:

# Clean build
pio run -t clean
```

### Flashing & Monitoring

```bash
# Flash firmware to device
pio run -e tbeam -t upload
./bin/device-install.sh         # Install script for released firmware
./bin/device-update.sh          # Update script for released firmware

# Monitor serial output
pio device monitor -e tbeam
pio device monitor --baud 115200
pio device monitor -f direct -e tbeam  # Raw serial output
```

### Debugging

```bash
# Debug native builds with GDB
./bin/native-gdbserver.sh       # Start GDB server
gdb .pio/build/native/program   # Attach GDB

# Decode ESP32 crash logs
python ./bin/exception_decoder.py <crash_log>

# Monitor Linux daemon logs
tail -f ~/.meshtastic/meshtasticd.log
```

### Build Scripts
- `bin/platformio-pre.py` - Pre-build script (runs before compilation)
- `bin/platformio-custom.py` - Custom build logic
- `bin/generate_ci_matrix.py` - Generate CI build targets

### Code Formatting & Linting

```bash
# Format code before commits (REQUIRED)
trunk fmt

# Run linting checks
trunk check

# Static analysis
pio check --flags "-DAPP_VERSION=1.0.0 --suppressions-list=suppressions.txt"
./bin/check-all.sh tbeam        # Check specific target
./bin/check-all.sh              # Check common targets
```

## Core Architecture

### 1. Packet Routing & Mesh Networking

**Packet Flow:**
```
Radio Hardware
  → RadioInterface (SX126xInterface, etc.)
  → Router.enqueueReceivedMessage()
  → fromRadioQueue
  → Router.handleReceived()
    → Decrypt (perhapsDecode)
    → Module dispatch (callModules)
    → Send to phone app
```

**Router Hierarchy:**
- **Router** (base) - Core packet handling, queue management (`src/mesh/Router.h`)
- **FloodingRouter** - Naive flooding broadcast strategy (`src/mesh/FloodingRouter.h`)
- **NextHopRouter** - Direct routing optimization with fallback to flooding (`src/mesh/NextHopRouter.h`)
- **ReliableRouter** - Adds ACK/NAK handling for reliable delivery

**Key Files:**
- `src/mesh/Router.{h,cpp}` - Base router implementation
- `src/mesh/FloodingRouter.{h,cpp}` - Flooding algorithm
- `src/mesh/NextHopRouter.h` - Next-hop routing

**MeshService** (`src/mesh/MeshService.h`):
- Central coordinator bridging Router and client apps (phone/web)
- Manages packet routing and queue management
- Handles phone app communication via Bluetooth/WiFi
- Processes commands from AdminModule

### 2. Module System

All feature modules inherit from `MeshModule` or `ProtobufModule<T>`.

**Base Class:** `src/mesh/MeshModule.h`

**Module Interface:**
```cpp
class MeshModule {
  virtual bool wantPacket(const meshtastic_MeshPacket *p);
  virtual ProcessMessage handleReceived(const meshtastic_MeshPacket &mp);
  virtual meshtastic_MeshPacket *allocReply();
  virtual int32_t runOnce();  // For OSThread-based modules
};
```

**Built-in Modules** (`src/modules/`):
- **AdminModule** - Device configuration, remote settings
- **TextMessageModule** - Text messaging
- **PositionModule** - GPS position sharing (broadcasts periodically)
- **NodeInfoModule** - Node information exchange
- **RoutingModule** - ACK/NAK handling, routing control
- **NeighborInfoModule** - Neighbor discovery
- **TraceRouteModule** - Route tracing/debugging
- **TelemetryModule** - Device telemetry (battery, temp, etc.)
- **StoreForwardModule** - Store-and-forward for ESP32
- **ExternalNotificationModule** - External notification control
- **SerialModule** - Serial port interface

**Pattern:** Modules can extend both `MeshModule` AND `OSThread` to handle periodic tasks.

### 3. Radio Interface Abstraction

**Base Class:** `src/mesh/RadioInterface.h`

**Concrete Implementations:**
- `SX126xInterface` - SX1262/SX1268 (most common)
- `SX128xInterface` - SX1280 (2.4 GHz)
- `RF95Interface` - RFM95 legacy
- `LR11x0Interface` - LR1110/LR1120/LR1121
- `STM32WLE5JCInterface` - STM32WLE5 integrated radio

**RadioLibInterface** (`src/mesh/RadioLibInterface.h`):
- Generic wrapper for RadioLib library
- ISR-driven transmit/receive
- Collision avoidance (CAD - Channel Activity Detection)
- Transmission queue with SNR-weighted backoff
- SPI locking via `LockingArduinoHal`

### 4. Configuration & Persistence

**NodeDB Class** (`src/mesh/NodeDB.h`):
- Single source of truth for device state, node database, and configuration
- Manages flash storage in `/prefs/` directory
- Stores: device state, global config, module config, channels, node database

**Storage Segments:**
```
/prefs/device.proto     - Device state (NodeNum, User)
/prefs/config.proto     - Global settings (radio, device role)
/prefs/module.proto     - Module-specific configs
/prefs/channels.proto   - Channel definitions + encryption keys
/prefs/nodes.proto      - Mesh node database
```

**Global Configuration Objects:**
```cpp
extern meshtastic_DeviceState devicestate;
extern meshtastic_NodeDatabase nodeDatabase;
extern meshtastic_ChannelFile channelFile;
extern meshtastic_LocalConfig config;
extern meshtastic_LocalModuleConfig moduleConfig;
extern NodeDB *nodeDB;
```

**Default Values:** Use helpers in `src/mesh/Default.h`:
```cpp
Default::getConfiguredOrDefaultMs(configured, default)
Default::getConfiguredOrMinimumValue(configured, min)
Default::getConfiguredOrDefaultMsScaled(configured, default, numNodes)
```

**Configuration Loading Sequence:**
1. Factory defaults from `src/configuration.h`
2. Variant-specific overrides from `variants/*/variant.h`
3. User configuration from persistent storage (`/prefs/`)
4. Runtime modifications via AdminModule

### 5. Threading & Concurrency

**OSThread Base Class** (`src/concurrency/OSThread.h`):
- Non-preemptive cooperative threading
- Override `runOnce()` which returns next interval in ms
- Two controllers: `mainController` and `timerController`

**Main Threads:**
- **Router** - Processes incoming packets from fromRadioQueue
- **RadioLibInterface** - Manages radio state machine (ISR-driven)
- **Module Threads** - Optional for modules needing periodic tasks (e.g., PositionModule)
- **UI Thread** - Screen updates
- **Bluetooth Thread** - BLE communication

**Thread Safety:**
```cpp
extern concurrency::Lock *cryptLock;  // Crypto operations
// SPI bus protected by LockingArduinoHal
```

**Pattern:** Packets flow through FreeRTOS queues; single-threaded processing prevents concurrent modification.

## Hardware Variants

Located in `variants/<arch>/<name>/`:

**Each variant has:**
- `variant.h` - Pin definitions and hardware capabilities
- `platformio.ini` - Build configuration

**Key defines in variant.h:**
```cpp
#define USE_SX1262           // Radio chip selection
#define HAS_GPS 1            // Hardware capabilities
#define HAS_SCREEN 1
#define LORA_CS 36           // Pin assignments
#define SX126X_DIO1 14       // Radio-specific pins
```

**Support Levels** (in platformio.ini):
```ini
custom_meshtastic_support_level = 1  # Built on every PR
custom_meshtastic_support_level = 2  # Built on merge to main
board_level = extra                   # Only on full releases
```

## Protobuf Messages

- Definitions: `protobufs/meshtastic/*.proto`
- Generated code: `src/mesh/generated/`
- Regenerate: `bin/regen-protos.sh` (or `bin/regen-protos.bat` on Windows)
- All message types prefixed with `meshtastic_`

## Coding Conventions

### Style
- Follow existing code style - **run `trunk fmt` before commits**
- Use `LOG_DEBUG`, `LOG_INFO`, `LOG_WARN`, `LOG_ERROR` for logging
- Use `assert()` for invariants

### Naming
- Classes: `PascalCase` (e.g., `PositionModule`, `NodeDB`)
- Functions/Methods: `camelCase` (e.g., `sendOurPosition`, `getNodeNum`)
- Constants/Defines: `UPPER_SNAKE_CASE` (e.g., `MAX_INTERVAL`, `ONE_DAY`)
- Member variables: `camelCase`
- Config defines: `USERPREFS_*` for user-configurable options

### Conditional Compilation
```cpp
#if !MESHTASTIC_EXCLUDE_GPS         // Feature exclusion
#ifdef ARCH_ESP32                    // Architecture-specific
#if defined(USE_SX1262)             // Radio-specific
#ifdef HAS_SCREEN                    // Hardware capability
#if USERPREFS_EVENT_MODE            // User preferences
```

## MQTT Integration

MQTT bridges mesh networks to the internet.

**Key Components:**
- `src/mqtt/MQTT.cpp` - Main MQTT client singleton
- `src/mqtt/ServiceEnvelope.cpp` - Protobuf wrapper for mesh packets
- `moduleConfig.mqtt` - Configuration

**Topic Structure:**
```
{root}/{channel_id}/{gateway_id}
```

**Default Configuration:**
```cpp
mqtt_address = "mqtt.meshtastic.org"
mqtt_username = "meshdev"
mqtt_password = "large4cats"
mqtt_root = "msh"
mqtt_encryption_enabled = true
mqtt_tls_enabled = false
```

**Key Concepts:**
- **Uplink** - Mesh packets TO MQTT broker (`uplink_enabled` per channel)
- **Downlink** - MQTT messages INTO mesh (`downlink_enabled` per channel)
- **Encryption** - When enabled, only encrypted packets sent (plaintext JSON disabled)
- **PKI Messages** - Special handling for encrypted DMs on "PKI" channel

## Important Considerations

### Traffic Management
The mesh has limited bandwidth. When modifying broadcast intervals:
- Respect minimum intervals on default/public channels
- Use `Default::getConfiguredOrMinimumValue()` to enforce minimums
- Consider `numOnlineNodes` scaling for congestion control
- Check `channels.isDefaultChannel(index)` - default channels get stricter rate limits

### Power Management
Many devices are battery-powered:
- Use `IF_ROUTER(routerVal, normalVal)` for role-based defaults
- Check `config.power.is_power_saving` for power-saving modes
- Implement proper `sleep()` methods in radio interfaces

### Channel Security
- `channels.isDefaultChannel(index)` - Check if using default/public settings
- Default channels get stricter rate limits to prevent abuse
- Private channels may have relaxed limits

## Companion App Integration

### API Interfaces

**Bluetooth Low Energy** (nRF52, ESP32):
- Primary interface for mobile apps
- Automatic discovery and pairing
- Packet streaming and configuration

**WiFi HTTP API** (ESP32):
- Web-based configuration interface
- JSON REST API for automation
- Access point mode for initial setup

**TCP/Serial API** (Linux):
- Command-line client interface
- Integration with existing systems
- Daemon mode for always-on operation

**Message Flow:**
```
Phone App → BLE/WiFi → Firmware
  → Firmware processes via AdminModule/MeshService
  → Radio Interface → Mesh Network
  → Remote Firmware → Radio → Local Firmware
  → BLE/WiFi → Phone App
```

## Debugging Mesh Networks

### Network Analysis

**Monitor Mesh Traffic:**
- Check SNR values for link quality assessment
- Analyze hop count for routing efficiency
- Monitor packet retransmission patterns
- Track channel utilization percentage

**Common Issues:**

**High Packet Loss:**
- Check channel congestion with `CHANNEL_UTILIZATION` telemetry
- Verify antenna connections
- Analyze frequency plan conflicts

**Poor Range:**
- Monitor received SNR values
- Check power settings and duty cycle limits
- Verify antenna orientation

**Routing Problems:**
- Enable routing debug logs
- Check node database synchronization
- Monitor hop limit handling

## Development Workflow

### Git Workflow

Clone with submodules:
```bash
git clone --recursive https://github.com/meshtastic/firmware
cd firmware
git submodule update --init
```

Create feature branch:
```bash
git checkout -b feature/my-feature
```

### Branch Strategy

- **master** - Latest stable release
- **develop** - Integration branch for new features
- **release/x.y.z** - Release preparation branches
- **feature/*** - New feature development

**Pull Request Requirements:**
- Successful CI builds on all platforms
- Code review approval
- CLA signature via GitHub integration
- Passing automated tests
- Code formatted with `trunk fmt`

## GitHub Actions CI/CD

**Key Workflows** (`.github/workflows/`):
- `main_matrix.yml` - Main CI pipeline (builds all targets on master/develop)
- `trunk_check.yml` - Code quality checks (must pass before merge)
- `test_native.yml` - Native platform unit tests
- `tests.yml` - End-to-end and hardware tests (runs daily)
- `release_channels.yml` - Release builds and packaging
- `nightly.yml` - Nightly builds from develop

**CI Matrix Generation:**
```bash
# Generate full build matrix
./bin/generate_ci_matrix.py all

# Generate PR-level matrix (subset for faster builds)
./bin/generate_ci_matrix.py all --level pr
```

## Common Development Tasks

### Adding a New Module
1. Create `src/modules/MyModule.cpp` and `.h`
2. Inherit from `MeshModule` or `ProtobufModule<T>`
3. Implement `handleReceivedProtobuf()` and optionally `runOnce()`
4. Register in `src/modules/Modules.cpp`
5. Add protobuf messages if needed in `protobufs/`
6. Regenerate protos: `bin/regen-protos.sh`

### Adding a New Hardware Variant
1. Create directory under `variants/<arch>/<name>/`
2. Add `variant.h` with pin definitions
3. Add `platformio.ini` with build config
4. Use `extends = <base_env>` to inherit common configs
5. Test build: `pio run -e <your_variant>`

### Modifying Configuration Defaults
1. Check `src/mesh/Default.h` for default value defines
2. Update initialization in `src/mesh/NodeDB.cpp`
3. Consider `isDefaultChannel()` checks for public channel restrictions
4. Test with fresh device (no saved config)

## Key Global Objects

```cpp
extern Router *router;                    // Global router instance
extern MeshService *service;              // Global mesh service
extern NodeDB *nodeDB;                    // Global node database

// Module singletons
extern TextMessageModule *textMessageModule;
extern PositionModule *positionModule;
extern RoutingModule *routingModule;
extern AdminModule *adminModule;
```

## Resources

- [Documentation](https://meshtastic.org/docs/)
- [Building Instructions](https://meshtastic.org/docs/development/firmware/build)
- [Flashing Instructions](https://meshtastic.org/docs/getting-started/flashing-firmware/)
