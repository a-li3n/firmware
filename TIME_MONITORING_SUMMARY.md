# Meshtastic Time Monitoring - Complete Summary

## What You Have

I've created a complete solution for monitoring time synchronization in your Meshtastic mesh network:

### Files Created

1. **`meshtastic_time_monitor.py`** - Main monitoring script (✨ NEW: TCP + Alerting support)
2. **`TIME_MONITOR_README.md`** - Comprehensive documentation
3. **`QUICK_START_TIME_MONITOR.md`** - Quick reference guide
4. **`TCP_AND_ALERTING_GUIDE.md`** - ✨ NEW: TCP connection and alerting guide
5. **`example_serial_output.txt`** - Sample serial output for reference

### New Features ✨

1. **TCP Connection Support** - Connect to embedded nodes running meshtasticd over port 4403
2. **Automatic Alerts** - Send messages to designated mesh channel when bad time detected
3. **Alert Cooldown** - Prevent spam with configurable cooldown periods
4. **Custom Messages** - Customize alert message format

## Quick Start (30 seconds)

```bash
# 1. Install dependencies
pip3 install pyserial meshtastic

# 2. Find your port (for serial)
ls /dev/tty* | grep -i usb    # Mac/Linux
# or check Device Manager         # Windows

# 3. Run it (Serial)
python3 meshtastic_time_monitor.py /dev/ttyUSB0

# Or via TCP (for embedded nodes)
python3 meshtastic_time_monitor.py --tcp localhost

# With automatic alerts
python3 meshtastic_time_monitor.py /dev/ttyUSB0 --alert --alert-channel 2
```

## How It Works

### The Problem
In mesh networks, nodes can have incorrect time if:
- Hardware RTC is not set
- GPS lock was never achieved
- Phone/NTP sync hasn't happened
- Node received bad time from another node

### The Solution
This script:
1. Monitors serial output from your Meshtastic device
2. Parses Position messages containing time information
3. Compares reported time to your system time
4. Identifies nodes with incorrect time
5. Provides statistics and reports

### What to Expect

**Good Output:**
```
✓ OK Node 0x87654321: Reported: 2026-01-10 18:30:45 UTC, Diff: 2s
```

**Problem Output:**
```
❌ INCORRECT Node 0x12345678: Reported: 2025-12-25 12:00:00 UTC, Diff: 15d 6h
  └─ WARNING: Time difference exceeds threshold!
```

## Key Concepts

### Time Quality in Meshtastic

Meshtastic uses a hierarchy of time sources (best to worst):

1. **GPS** - Most accurate (~1 second)
2. **NTP/Phone** - Very accurate (~5 seconds)
3. **Mesh Network** - Depends on source quality
4. **Hardware RTC** - Drifts over time
5. **None** - No time set

### Position Messages

- Position messages include a `time` field (Unix timestamp)
- Only sent by nodes with quality time sources (GPS or NTP)
- Only transmitted on PRIMARY channels
- Nodes without good time can sync from these messages

### Serial Output Format

The firmware logs packets in two formats:

**Text Format:**
```
handleReceived(REMOTE) (id=0x12345678 fr=0x87654321 to=0xffffffff ... Portnum=3 rxtime=1704988800)
Position packet: time=1704988795 lat=374544000 lon=-1220569000
```

**JSON Format** (if enabled):
```json
{"from":2271560481,"type":"position","payload":{"time":1704988795,...}}
```

## Common Scenarios

### Scenario 1: Finding Bad Nodes

**Goal:** Identify which nodes in your mesh have incorrect time

**Steps:**
1. Connect your node via USB
2. Run the monitor for 10-15 minutes
3. Press Ctrl+C to see final statistics
4. Check "NODES WITH INCORRECT TIME" section

**Command:**
```bash
python3 meshtastic_time_monitor.py /dev/ttyUSB0 --threshold 60
```

### Scenario 2: Verifying Time Sync

**Goal:** Confirm a node's time is now correct after syncing

**Steps:**
1. Note the node ID with bad time
2. Set time on that node (see fixing section below)
3. Wait 2-3 minutes for next position broadcast
4. Verify node shows ✓ OK in output

**Command:**
```bash
# Monitor
python3 meshtastic_time_monitor.py /dev/ttyUSB0 --threshold 30

# In another terminal, fix the node
meshtastic --dest <bad_node_id> --set-time
```

### Scenario 3: Tracking Time Drift

**Goal:** Determine if a node's RTC is faulty

**Steps:**
1. Run monitor with strict threshold for several hours
2. Check if time difference increases over time
3. A good RTC should maintain accuracy within 10-30 seconds/day

**Command:**
```bash
python3 meshtastic_time_monitor.py /dev/ttyUSB0 --threshold 10 --stats-interval 300
```

## Fixing Incorrect Time

### Method 1: Meshtastic CLI (Recommended)

```bash
# Set time on locally connected node
meshtastic --set-time

# Set time on specific remote node
meshtastic --dest <node_id> --set-time
```

### Method 2: Mobile App

1. Open Meshtastic app
2. Connect to node via Bluetooth
3. Time automatically syncs from phone
4. Wait for next position broadcast (~15-30 minutes)

### Method 3: GPS Lock

If node has GPS:
1. Place node outdoors with clear sky view
2. Wait 5-15 minutes for GPS lock
3. Time will automatically set from GPS
4. This is the most accurate method

### Method 4: Mesh Sync (Automatic)

- Nodes without time will automatically sync from mesh
- Requires at least one node with good time in range
- May take 15-30 minutes (position broadcast interval)
- Quality will be RTCQualityFromNet (lower than GPS/NTP)

## Troubleshooting

### "Permission denied"
```bash
sudo usermod -a -G dialout $USER
# Then log out and log back in
```

### "No such file or directory"
- Wrong port! Use `ls /dev/tty*` to find correct port
- Try `/dev/ttyUSB0`, `/dev/ttyACM0`, `/dev/cu.usbserial-*`

### No Output Showing
- Wait 1-2 minutes - position broadcasts are periodic
- Check that position module is enabled on nodes
- Verify log level is INFO or DEBUG in firmware

### Only Seeing Encrypted Packets
- Script can't decode encrypted data
- This is normal - only decrypted packets show position
- Ensure your node is on the PRIMARY channel

## Understanding the Statistics

### Sample Output
```
Node: 0x87654321
  Samples: 15              ← Number of position updates received
  Average time diff: 3s    ← Average difference from correct time
  Max time diff: 8s        ← Worst difference observed
  Last seen: ...           ← When last position was received
  Last reported time: ...  ← Time value from last position
```

### What's Good?
- Average diff < 10s: Excellent
- Max diff < 30s: Good
- Consistent samples: Node is actively broadcasting

### What's Bad?
- Average diff > 1 minute: Time sync issue
- Max diff > 5 minutes: Serious problem
- Increasing max diff: RTC drift problem

## Advanced Usage

### JSON Logging

For more detailed packet information, enable JSON logging in firmware:

```bash
# Edit platformio.ini
# Add to your environment's build_flags:
-DENABLE_JSON_LOGGING=1

# Rebuild and flash
pio run -e <your_board> -t upload

# Run monitor with JSON flag
python3 meshtastic_time_monitor.py /dev/ttyUSB0 --json
```

### Custom Threshold

Different use cases need different thresholds:

```bash
# Strict (GPS-level accuracy)
python3 meshtastic_time_monitor.py /dev/ttyUSB0 --threshold 5

# Normal (NTP-level accuracy)
python3 meshtastic_time_monitor.py /dev/ttyUSB0 --threshold 30

# Relaxed (mesh-sync level)
python3 meshtastic_time_monitor.py /dev/ttyUSB0 --threshold 300
```

### Statistics Interval

Control how often statistics are printed:

```bash
# Every 2 minutes
python3 meshtastic_time_monitor.py /dev/ttyUSB0 --stats-interval 120

# Every 10 minutes
python3 meshtastic_time_monitor.py /dev/ttyUSB0 --stats-interval 600
```

## Technical Background

### Code References

Key files in Meshtastic firmware:

- **`src/gps/RTC.cpp`** - Time quality management
- **`src/modules/PositionModule.cpp`** - Position broadcasting with time
- **`protobufs/meshtastic/mesh.proto`** - Position message definition
- **`src/mesh/Router.cpp`** - Packet timestamping

### Time Quality Levels

```cpp
enum RTCQuality {
    RTCQualityNone = 0,        // No time set
    RTCQualityDevice = 1,      // Hardware RTC only
    RTCQualityFromNet = 2,     // Time from mesh
    RTCQualityNTP = 3,         // Phone/NTP time
    RTCQualityGPS = 4          // GPS time (best)
};
```

### Position Message Structure

```protobuf
message Position {
    fixed32 time = 4;                  // Seconds since 1970
    int32 latitude_i = 1;              // Latitude * 1e7
    int32 longitude_i = 2;             // Longitude * 1e7
    int32 altitude = 3;                // Meters
    fixed32 timestamp = 7;             // GPS timestamp
    int32 timestamp_millis_adjust = 8; // Milliseconds
    // ... other fields
}
```

## Real-World Examples

### Example 1: New Mesh Network Setup

**Scenario:** You just set up 5 new nodes, want to verify time sync

**Steps:**
1. Connect one node with GPS, wait for GPS lock
2. Connect monitoring node via USB
3. Run monitor for 30 minutes
4. All nodes should sync from GPS node
5. Verify all show ✓ OK with diff < 30s

### Example 2: Troubleshooting Solar Node

**Scenario:** Solar-powered node in field keeps reporting wrong time

**Steps:**
1. Bring node home, connect USB
2. Run monitor to confirm bad time
3. Set time via CLI: `meshtastic --set-time`
4. Monitor for 10 minutes to verify
5. Return node to field
6. If time drifts again, RTC battery may be dead

### Example 3: Multi-Hop Network

**Scenario:** Large mesh, want to ensure time propagates correctly

**Steps:**
1. Place monitoring node in center of mesh
2. Run monitor for several hours
3. Track max diff for each node
4. Nodes 1-2 hops from GPS should be < 30s
5. Nodes 3+ hops may be 30s-2m (acceptable)
6. Any node > 5m needs investigation

## Support & Resources

### Documentation
- **TIME_MONITOR_README.md** - Full documentation
- **QUICK_START_TIME_MONITOR.md** - Quick reference
- **example_serial_output.txt** - Sample output format

### Meshtastic Resources
- [Official Docs](https://meshtastic.org/docs/)
- [Firmware Source](https://github.com/meshtastic/firmware)
- [Python CLI](https://github.com/meshtastic/python)

### Getting Help

If you encounter issues:
1. Check the troubleshooting sections in README
2. Verify your serial port and permissions
3. Try with different threshold values
4. Enable JSON logging for more detail
5. Check Meshtastic Discord/Forum for support

## Next Steps

1. **Test the script** with example data
2. **Connect to your node** and run live monitoring
3. **Identify problem nodes** in your mesh
4. **Fix time** on those nodes
5. **Monitor again** to verify fixes
6. **Set up periodic monitoring** if needed

## Script Limitations

Current limitations to be aware of:

- **Requires serial connection** - Can't monitor over BLE/WiFi
- **Text parsing** - May miss some packets if log format changes
- **No decryption** - Can't see time in encrypted packets
- **Position only** - Only tracks time in position messages
- **Single port** - Monitors one node at a time

Potential enhancements:
- Multi-port support for monitoring multiple nodes
- BLE/WiFi connectivity
- Web dashboard
- Database logging
- Alert notifications
- Node name resolution

## Final Notes

This tool helps identify time synchronization issues in Meshtastic networks, which is important for:

- **Message ordering** - Correct timestamps for message history
- **Telemetry** - Accurate time for sensor readings
- **Store & Forward** - Proper message queuing and expiration
- **Debugging** - Correlation of events across nodes
- **User Experience** - Messages show correct send time in apps

Good time synchronization improves overall mesh network reliability and user experience!
