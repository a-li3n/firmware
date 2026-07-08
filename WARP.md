# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Overview

This is the Meshtastic firmware repository - an open-source LoRa mesh networking project for ESP32, nRF52, RP2040/RP2350, and Linux platforms. The firmware enables decentralized communication over long distances without cellular or internet infrastructure.

## Development Commands

### Build Commands

Build for a specific target board:
```bash
pio run -e tbeam                 # Build for TTGO T-Beam
pio run -e heltec-v2.1          # Build for Heltec LoRa v2.1
pio run -e rak4631              # Build for RAK4631 (nRF52)
pio run -e pico                 # Build for Raspberry Pi Pico
```

Platform-specific builds:
```bash
./bin/build-esp32.sh tbeam      # ESP32 platform
./bin/build-nrf52.sh rak4631    # nRF52 platform  
./bin/build-rp2xx0.sh pico      # RP2040/RP2350 platform
./bin/build-native.sh           # Linux native build
```

List all available board targets:
```bash
pio project data | grep env:
```

Build all targets for CI/testing:
```bash
python ./bin/generate_ci_matrix.py esp32    # Generate ESP32 target list
```

### Testing Commands

Run native platform tests:
```bash
pio test -e native              # Unit tests on native platform
pio test -e coverage            # Unit tests with coverage
platformio test -e coverage -v --junit-output-path testreport.xml
```

Run integration tests with simulator:
```bash
.pio/build/coverage/program &   # Start simulator
python3 -c 'from meshtastic.test import testSimulator; testSimulator()'
```

Hardware-in-loop testing:
```bash
./bin/test-simulator.sh         # End-to-end simulator test
```

### Code Quality Commands

Static analysis and checking:
```bash
pio check --flags "-DAPP_VERSION=1.0.0 --suppressions-list=suppressions.txt"
./bin/check-all.sh tbeam        # Check specific target
./bin/check-all.sh              # Check common targets
```

Code formatting:
```bash
trunk fmt                       # Format all code using Trunk
trunk check                     # Run all linters and checks
```

### Deployment Commands  

Flash firmware to device:
```bash
pio run -e tbeam -t upload      # Build and flash to device
./bin/device-install.sh         # Install script for released firmware
./bin/device-update.sh          # Update script for released firmware
```

Monitor serial output:
```bash
pio device monitor -e tbeam     # Serial monitor for specific target
pio device monitor --baud 115200
```

### Debug Commands

Debug with GDB (native builds):
```bash
./bin/native-gdbserver.sh       # Start GDB server for native debugging
gdb .pio/build/native/program   # Attach GDB to native build
```

Exception decoding:
```bash
python ./bin/exception_decoder.py <crash_log>  # Decode ESP32 crash logs
```

## Code Architecture

### Core Components

**Main Application** (`src/main.cpp`):
- Hardware initialization and platform detection
- Service startup and coordination  
- Main event loop and power management

**MeshService** (`src/mesh/MeshService.h`):
- Central coordination of mesh networking
- Packet routing and queue management
- Phone app communication via Bluetooth/WiFi

**RadioInterface Hierarchy**:
- `RadioInterface`: Base class for all radio drivers
- `SX1262Interface`, `SX1268Interface`: Semtech SX126x drivers
- `RF95Interface`: Semtech SX127x (RFM95) driver  
- `SX1280Interface`: 2.4GHz Semtech SX1280 driver
- `LR11xxInterface`: Semtech LR11xx drivers with GNSS

### Module System

**ProtobufModule Base Class** (`src/mesh/ProtobufModule.h`):
All application modules inherit from this class and handle specific Protocol Buffer message types.

**Key Modules**:
- `AdminModule`: Device configuration and management
- `RoutingModule`: Mesh routing and packet forwarding  
- `PositionModule`: GPS/GNSS position sharing
- `TextMessageModule`: Text messaging functionality
- `TelemetryModule`: Environmental sensor data
- `RemoteHardwareModule`: GPIO control over mesh

**Module Discovery**: Modules are auto-registered via `setupModules()` in `src/modules/Modules.cpp`

### Platform Abstraction

**Platform Layer** (`src/platform/`):
- `esp32/`: ESP32-specific implementations
- `nrf52/`: Nordic nRF52-specific code
- `rp2xx0/`: Raspberry Pi Pico implementations  
- `portduino/`: Linux native platform layer

**Hardware Variants** (`variants/`):
- Board-specific pin definitions and configurations
- Each variant has `variant.h` and optional `platformio.ini`
- Organized by platform: `esp32/`, `nrf52840/`, `rp2040/`, etc.

### Protocol Buffer Integration

**Generated Code** (`src/mesh/generated/`):
- Auto-generated from `.proto` files in `protobufs/` submodule
- Core types: `meshtastic_MeshPacket`, `meshtastic_Config`, etc.
- Regenerate with: `./bin/regen-protos.sh`

**Key Message Types**:
- `MeshPacket`: Wire format for all mesh messages
- `AdminMessage`: Administrative commands
- `Position`: GPS coordinates and metadata
- `Telemetry`: Sensor data and device metrics

### Configuration System

**NodeDB** (`src/NodeDB.h`):
- Persistent storage of configuration and node database
- Flash-based storage with wear leveling
- Manages channels, user settings, and device configuration

**Configuration Loading**:
1. Factory defaults from `src/configuration.h`
2. Variant-specific overrides from `variants/*/variant.h`  
3. User configuration from persistent storage
4. Runtime modifications via AdminModule

## Hardware Variant Development

### Adding New Hardware

1. **Create variant directory**: `variants/{platform}/{board_name}/`

2. **Create variant.h** with pin definitions:
```cpp
#define LORA_SCK 5
#define LORA_MISO 19  
#define LORA_MOSI 27
#define LORA_CS 18
#define LORA_DIO0 26
#define LORA_RST 23
#define LORA_DIO1 33
```

3. **Add platformio.ini configuration**:
```ini
[env:myboard]
extends = esp32_base
board = esp32dev  
build_flags = 
  ${esp32_base.build_flags}
  -I variants/esp32/myboard
  -D MYBOARD_VARIANT
```

4. **Test the variant**:
```bash
pio run -e myboard
```

### Radio Configuration

**Frequency Plans** (`src/mesh/RadioInterface.cpp`):
Frequency selection is automatic based on:
- Hardware region detection (GPIO strapping)
- Regulatory database in `src/mesh/FrequencyList.h`  
- User configuration override

**Power and Range Tuning**:
- Modify `txPower` in LoRa region configurations
- Adjust spreading factor `sf` and bandwidth `bw` for range vs. speed
- Consider duty cycle regulations per region

## Module Development  

### Creating New Modules

1. **Inherit from ProtobufModule**:
```cpp
class MyModule : public ProtobufModule<meshtastic_MyMessage>
{
  protected:
    virtual bool handleReceivedProtobuf(const meshtastic_MeshPacket &mp, 
                                       meshtastic_MyMessage *p) override;
}
```

2. **Register in Modules.cpp**:
```cpp
myModule = new MyModule();
```

3. **Define Protocol Buffer message** in `protobufs/` submodule

4. **Handle power management**:
```cpp
virtual void onSleep() override { /* prepare for sleep */ }
virtual void onWake() override { /* wake up actions */ }
```

### Module Communication Patterns

**Broadcast Messages**: Send to `NODENUM_BROADCAST`
**Direct Messages**: Send to specific NodeNum  
**Local Processing**: Use `handleReceived()` for non-protobuf packets
**Phone Integration**: Override `getUIFrameState()` for app display

## Debugging Mesh Networks

### Network Analysis

Monitor mesh traffic:
```bash
pio device monitor -f direct -e tbeam   # Raw serial output
tail -f ~/.meshtastic/meshtasticd.log   # Linux daemon logs
```

**Key Debug Information**:
- SNR values for link quality assessment
- Hop count analysis for routing efficiency  
- Packet retransmission patterns
- Channel utilization percentage

### Common Issues

**High Packet Loss**:
- Check channel congestion with `CHANNEL_UTILIZATION` telemetry
- Verify antenna connections and SWR
- Analyze frequency plan conflicts

**Poor Range Performance**:  
- Monitor received SNR values
- Check power settings and duty cycle limits
- Verify antenna radiation pattern orientation

**Routing Loops**:
- Enable routing debug logs
- Check node database synchronization
- Monitor hop limit handling

## Power Optimization

### Sleep Mode Implementation

**Light Sleep** (ESP32):
- CPU stops, radio stays active for wake on packet
- Automatic in `PowerFSM.cpp` based on activity

**Deep Sleep** (ESP32):
- Everything off except RTC
- Wake on timer, button, or external interrupt
- Configure in device settings

### Battery Monitoring

**Built-in ADC Reading**:
```cpp
float batteryVoltage = readBatteryLevel();  // Platform-specific
```

**Power Telemetry**:
- Battery voltage reporting
- Charging status detection  
- Power consumption estimates

## Development Environment

### Required Tools

- **PlatformIO Core** 6.0+ with PlatformIO extension for VS Code
- **Python 3.8+** for build scripts and protocol buffer generation
- **Git** with submodules support (`git submodule update --init`)

### Workflow

1. **Fork and clone** with submodules:
```bash
git clone --recursive https://github.com/yourusername/firmware
```

2. **Create feature branch**:
```bash
git checkout -b feature/my-awesome-feature
```

3. **Build and test**:
```bash
pio run -e tbeam
pio test -e native
```

4. **Format code**:
```bash
trunk fmt
```

5. **Create pull request** with detailed description and test results

### Branch Strategy

- **master**: Latest stable release
- **develop**: Integration branch for new features  
- **release/x.y.z**: Release preparation branches
- **feature/***: New feature development

Pull requests require:
- Successful CI builds on all platforms
- Code review approval  
- CLA signature via GitHub integration
- Passing automated tests

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

### Message Flow

1. **Phone App** → **BLE/WiFi** → **Firmware**
2. **Firmware** processes via **AdminModule** or **MeshService** 
3. **Firmware** → **Radio Interface** → **Mesh Network**
4. **Remote Firmware** → **Radio Interface** → **Local Firmware**
5. **Local Firmware** → **BLE/WiFi** → **Phone App**

Understanding this flow is essential for debugging client connectivity issues and implementing new API features.