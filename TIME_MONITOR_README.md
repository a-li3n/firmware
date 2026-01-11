# Meshtastic Time Synchronization Monitor

## Overview

This tool monitors serial output from a Meshtastic device to track which nodes are sending time information to the mesh network and identifies nodes with incorrect time settings.

## How Time Works in Meshtastic

### Time Quality Hierarchy

Meshtastic uses a time quality hierarchy to determine which time sources to trust:

1. **RTCQualityGPS** (Highest) - Time from GPS satellites
2. **RTCQualityNTP** - Time from NTP server or phone app
3. **RTCQualityFromNet** - Time from other mesh nodes
4. **RTCQualityDevice** - Hardware RTC only
5. **RTCQualityNone** (Lowest) - No time set

### Time Transmission

- Time is transmitted primarily through **Position messages** with a `time` field (seconds since Unix epoch)
- Only nodes with quality time (RTCQualityNTP or RTCQualityGPS) include time in position broadcasts
- Time is only transmitted on **PRIMARY channels**
- Nodes without good time sources accept time from mesh (RTCQualityFromNet)

### Position Message Structure

```protobuf
message Position {
    fixed32 time = 4;              // seconds since 1970 - used to set local RTC
    fixed32 timestamp = 7;          // GPS solution timestamp
    int32 timestamp_millis_adjust = 8;  // milliseconds adjustment
}
```

### Important Files

- **src/gps/RTC.cpp/h** - Central time management
- **src/modules/PositionModule.cpp** - Sends/receives position with time
- **protobufs/meshtastic/mesh.proto** - Position message definition

## Installation

### Prerequisites

```bash
# Python 3.6 or higher
python3 --version

# Install pyserial
pip3 install pyserial
```

### Setup

```bash
# Make the script executable
chmod +x meshtastic_time_monitor.py
```

## Usage

### Basic Usage

```bash
# Linux/Mac
python3 meshtastic_time_monitor.py /dev/ttyUSB0

# Windows
python3 meshtastic_time_monitor.py COM3
```

### Advanced Options

```bash
# Set custom baud rate
python3 meshtastic_time_monitor.py /dev/ttyUSB0 --baud 115200

# Set time difference threshold (default: 30 seconds)
python3 meshtastic_time_monitor.py /dev/ttyUSB0 --threshold 60

# Parse JSON formatted logs (for ENABLE_JSON_LOGGING builds)
python3 meshtastic_time_monitor.py /dev/ttyUSB0 --json

# Change statistics interval (default: 60 seconds)
python3 meshtastic_time_monitor.py /dev/ttyUSB0 --stats-interval 120
```

### Full Example

```bash
# Monitor with 60-second threshold, JSON parsing, stats every 2 minutes
python3 meshtastic_time_monitor.py /dev/ttyUSB0 --threshold 60 --json --stats-interval 120
```

## Finding Your Serial Port

### Linux

```bash
# List USB serial devices
ls /dev/ttyUSB*
ls /dev/ttyACM*

# Or use dmesg to see what was connected
dmesg | grep tty
```

### macOS

```bash
# List serial devices
ls /dev/cu.*
ls /dev/tty.usb*

# Common ESP32 devices
ls /dev/cu.SLAB_USBtoUART
ls /dev/cu.usbserial-*
```

### Windows

```bash
# List COM ports in PowerShell
[System.IO.Ports.SerialPort]::getportnames()

# Or check Device Manager -> Ports (COM & LPT)
```

## Output Examples

### Real-time Monitoring

```
[+] Connected to /dev/ttyUSB0 at 115200 baud
[+] Monitoring for time synchronization issues (threshold: 30s)
[+] Press Ctrl+C to stop and show statistics

✓ OK Node 0x87654321: Reported: 2026-01-10 18:30:45 UTC, Diff: 2s
❌ INCORRECT Node 0x12345678: Reported: 2025-12-25 12:00:00 UTC, Diff: 15d 6h
  └─ WARNING: Time difference exceeds threshold!
✓ OK Node 0xabcdef00: Reported: 2026-01-10 18:30:50 UTC, Diff: 5s
```

### Periodic Statistics

```
======================================================================
STATISTICS SUMMARY
======================================================================

Node: 0x87654321
  Samples: 15
  Average time diff: 3s
  Max time diff: 8s
  Last seen: 2026-01-10 18:35:22 UTC
  Last reported time: 2026-01-10 18:35:20 UTC

Node: 0x12345678
  Samples: 8
  Average time diff: 15d 6h
  Max time diff: 15d 7h
  Last seen: 2026-01-10 18:35:15 UTC
  Last reported time: 2025-12-25 12:05:30 UTC
======================================================================
```

### Final Report (on Ctrl+C)

```
======================================================================
FINAL STATISTICS
======================================================================

❌ NODES WITH INCORRECT TIME (2):

  Node: 0x12345678
    Samples: 23
    Average diff: 15d 6h
    Max diff: 15d 8h
    Last reported: 2025-12-25 12:15:45 UTC

  Node: 0xdeadbeef
    Samples: 5
    Average diff: 2h 15m
    Max diff: 2h 30m
    Last reported: 2026-01-10 16:05:12 UTC

✓ NODES WITH CORRECT TIME (3):
  0x87654321: avg diff 3s, 45 samples
  0xabcdef00: avg diff 5s, 32 samples
  0x11223344: avg diff 2s, 18 samples
======================================================================
```

## Understanding the Output

### Status Indicators

- **✓ OK** - Node's time is within the threshold
- **❌ INCORRECT** - Node's time differs by more than the threshold
- **WARNING** - Alert for nodes exceeding the threshold

### Node Identification

Nodes are identified by their hex ID (e.g., `0x87654321`). This is the node's unique identifier on the mesh network.

### Time Difference

The time difference shows how far off the node's reported time is from your local system time:
- `2s` - 2 seconds
- `5m 30s` - 5 minutes 30 seconds
- `2h 15m` - 2 hours 15 minutes
- `15d 6h` - 15 days 6 hours

## Troubleshooting

### No Output

1. **Check serial port permissions:**
   ```bash
   # Linux
   sudo usermod -a -G dialout $USER
   # Log out and back in

   # Or use sudo (not recommended)
   sudo python3 meshtastic_time_monitor.py /dev/ttyUSB0
   ```

2. **Verify correct port:**
   ```bash
   # Test connection
   pio device monitor -e <your_board>
   ```

3. **Check baud rate:**
   - Default is 115200, but some devices use different rates
   - Try `--baud 921600` or `--baud 57600`

### No Position Messages

1. **Enable position broadcasting:**
   - Use the Meshtastic app to configure position updates
   - Ensure position module is enabled in device settings

2. **Check log level:**
   - The device must have logging enabled
   - Check that `LOG_INFO` or `LOG_DEBUG` is active

3. **Try JSON mode:**
   - If your firmware is built with `ENABLE_JSON_LOGGING`, use `--json` flag
   - This provides more detailed packet information

### Permission Denied

```bash
# Linux - Add user to dialout group
sudo usermod -a -G dialout $USER

# macOS - No special permissions needed usually

# Windows - Run as Administrator or check device drivers
```

## Interpreting Results

### Common Scenarios

1. **Node with GPS:**
   - Should have time accurate to within 1-2 seconds
   - Consistent small differences are normal due to GPS update intervals

2. **Node with Phone/NTP:**
   - Should be accurate to within 5-10 seconds
   - May drift between updates (every 12 hours)

3. **Node receiving from Mesh:**
   - Accuracy depends on source node quality
   - May accumulate error if receiving from poor quality source

4. **Node with RTC only:**
   - May drift significantly over time (minutes to hours per day)
   - Should eventually sync from mesh if receiving position messages

### Red Flags

- **Large constant offset** (hours/days) - Node's RTC was set incorrectly or has bad time source
- **Increasing drift** - Node's RTC is failing or has poor quality crystal
- **Random time jumps** - Node is switching between conflicting time sources

## Fixing Incorrect Time

### Using Meshtastic CLI

```bash
# Connect to device
meshtastic --host /dev/ttyUSB0

# Set time from your computer
meshtastic --set-time

# Or set specific time
meshtastic --set-time 1704988800  # Unix timestamp
```

### Using Python API

```python
import meshtastic
import meshtastic.serial_interface
import time

# Connect to device
interface = meshtastic.serial_interface.SerialInterface('/dev/ttyUSB0')

# Set current time
interface.sendAdminMessage(time.time())

# Close connection
interface.close()
```

### Via Mobile App

1. Open Meshtastic app
2. Connect to node
3. Go to Settings → Radio Configuration
4. Time will automatically sync from phone

## Advanced: Enabling JSON Logging

To get more detailed logs, you can build firmware with JSON logging enabled:

```bash
# Edit platformio.ini for your environment
# Add to build_flags:
-DENABLE_JSON_LOGGING=1

# Rebuild
pio run -e <your_board>

# Flash
pio run -e <your_board> -t upload

# Run monitor with JSON flag
python3 meshtastic_time_monitor.py /dev/ttyUSB0 --json
```

## Technical Details

### Portnum for Position Messages

Position messages use `meshtastic_PortNum_POSITION_APP = 3`

### Time Field

The `time` field in Position messages is:
- Type: `fixed32` (4 bytes)
- Format: Seconds since Unix epoch (January 1, 1970 00:00:00 UTC)
- Range: 0 to 4,294,967,295 (year 2106)

### Reception Timestamp

Every packet also has an `rx_time` field set by the receiving node:
- This is the local time when the packet was received
- Different from the position `time` field which is when the position was measured

## Contributing

Issues and improvements welcome! Key areas for enhancement:
- Add node name resolution from NodeDB
- Support for multiple serial ports simultaneously
- Web dashboard for monitoring
- Alert notifications (email, webhook)
- Historical data logging to database

## License

This script is provided as-is for monitoring Meshtastic devices. Use at your own risk.

## See Also

- [Meshtastic Documentation](https://meshtastic.org/docs/)
- [Meshtastic Firmware Source](https://github.com/meshtastic/firmware)
- [Position Module Code](src/modules/PositionModule.cpp)
- [RTC Time Management Code](src/gps/RTC.cpp)
