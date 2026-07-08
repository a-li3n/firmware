# Quick Start: Meshtastic Time Monitor

## 1-Minute Setup

```bash
# Install dependencies
pip3 install pyserial meshtastic

# Find your serial port
ls /dev/tty*    # Mac/Linux
# or check Device Manager on Windows

# Run the monitor (Serial)
python3 meshtastic_time_monitor.py /dev/ttyUSB0

# Or run via TCP (for embedded nodes)
python3 meshtastic_time_monitor.py --tcp localhost
```

## Common Commands

### Serial Connection

```bash
# Basic monitoring (30 second threshold)
python3 meshtastic_time_monitor.py /dev/ttyUSB0

# Strict monitoring (10 second threshold)
python3 meshtastic_time_monitor.py /dev/ttyUSB0 --threshold 10

# Relaxed monitoring (5 minute threshold)
python3 meshtastic_time_monitor.py /dev/ttyUSB0 --threshold 300

# Use JSON logs (if firmware has ENABLE_JSON_LOGGING)
python3 meshtastic_time_monitor.py /dev/ttyUSB0 --json
```

### TCP Connection (Embedded Nodes)

```bash
# Connect to local meshtasticd
python3 meshtastic_time_monitor.py --tcp localhost

# Connect to remote node
python3 meshtastic_time_monitor.py --tcp 192.168.1.100

# TCP with custom port
python3 meshtastic_time_monitor.py --tcp localhost --tcp-port 4403
```

### With Automatic Alerts

```bash
# Enable alerts (sends message to mesh when bad time detected)
python3 meshtastic_time_monitor.py /dev/ttyUSB0 --alert

# Alert on specific channel
python3 meshtastic_time_monitor.py /dev/ttyUSB0 --alert --alert-channel 2

# Alert once per node (no cooldown)
python3 meshtastic_time_monitor.py /dev/ttyUSB0 --alert --alert-once

# TCP with alerts
python3 meshtastic_time_monitor.py --tcp localhost --alert --alert-channel 2
```

## What to Look For

### Good Signs ✓
```
✓ OK Node 0x87654321: Reported: 2026-01-10 18:30:45 UTC, Diff: 2s
✓ OK Node 0xabcdef00: Reported: 2026-01-10 18:30:50 UTC, Diff: 5s
```
These nodes have accurate time (within threshold).

### Problem Signs ❌
```
❌ INCORRECT Node 0x12345678: Reported: 2025-12-25 12:00:00 UTC, Diff: 15d 6h
  └─ WARNING: Time difference exceeds threshold!
```
This node's time is off by 15 days! It needs time correction.

## Quick Fixes

### Fix Local Node Time (USB connected)

```bash
# Using Meshtastic CLI
meshtastic --set-time

# Or using serial monitor
pio device monitor -e tbeam
# Then in another terminal:
meshtastic --set-time
```

### Fix Remote Node Time

1. **If node has GPS:** Wait for GPS fix (may take 5-15 minutes)
2. **If node has WiFi/BLE to phone:** Connect via app, time syncs automatically
3. **If node is mesh-only:** It will sync from other nodes with good time

## Understanding Output

| Time Diff | Meaning | Action |
|-----------|---------|--------|
| < 10s | Excellent | None needed |
| 10s - 1m | Good | Normal for mesh nodes |
| 1m - 10m | Acceptable | Check if node has GPS/NTP |
| > 10m | Problem | Needs manual time set |
| > 1 hour | Serious | Node RTC may be broken |

## Troubleshooting

### "Permission denied" Error
```bash
# Linux/Mac
sudo usermod -a -G dialout $USER
# Then log out and back in
```

### "No such file or directory"
```bash
# Wrong port! Find the right one:
ls /dev/tty* | grep -i usb
```

### No Output After Connecting
- Wait 1-2 minutes for position broadcasts
- Check that position module is enabled on nodes
- Try increasing log level on device if possible

## Example Session

```
$ python3 meshtastic_time_monitor.py /dev/ttyUSB0
[+] Connected to /dev/ttyUSB0 at 115200 baud
[+] Monitoring for time synchronization issues (threshold: 30s)
[+] Press Ctrl+C to stop and show statistics

✓ OK Node 0x87654321: Reported: 2026-01-10 18:30:45 UTC, Diff: 2s
❌ INCORRECT Node 0x12345678: Reported: 2025-12-25 12:00:00 UTC, Diff: 15d 6h
  └─ WARNING: Time difference exceeds threshold!
✓ OK Node 0xabcdef00: Reported: 2026-01-10 18:30:50 UTC, Diff: 5s
✓ OK Node 0x87654321: Reported: 2026-01-10 18:31:45 UTC, Diff: 1s

^C
[+] Stopping monitor...

======================================================================
FINAL STATISTICS
======================================================================

❌ NODES WITH INCORRECT TIME (1):

  Node: 0x12345678
    Samples: 3
    Average diff: 15d 6h
    Max diff: 15d 6h
    Last reported: 2025-12-25 12:02:15 UTC

✓ NODES WITH CORRECT TIME (2):
  0x87654321: avg diff 2s, 8 samples
  0xabcdef00: avg diff 5s, 3 samples
======================================================================
```

## Next Steps

For detailed information, see [TIME_MONITOR_README.md](TIME_MONITOR_README.md)

## Common Use Cases

### Case 1: Find Nodes with Bad Time
**Goal:** Identify which nodes need time correction

```bash
python3 meshtastic_time_monitor.py /dev/ttyUSB0 --threshold 60
# Run for 5-10 minutes, press Ctrl+C
# Check "NODES WITH INCORRECT TIME" section
```

### Case 2: Verify Time After Sync
**Goal:** Confirm nodes fixed their time

```bash
# Before sync
python3 meshtastic_time_monitor.py /dev/ttyUSB0 --threshold 30
# Note the bad nodes

# Set time on those nodes
meshtastic --dest <node_id> --set-time

# After sync (wait 2-3 minutes for position broadcast)
python3 meshtastic_time_monitor.py /dev/ttyUSB0 --threshold 30
# Verify nodes now show ✓ OK
```

### Case 3: Monitor Time Drift
**Goal:** Track if a node's RTC is drifting over time

```bash
python3 meshtastic_time_monitor.py /dev/ttyUSB0 --threshold 10 --stats-interval 300
# Let run for hours/days
# Check if average/max diff increases over time
```

### Case 4: Debug Time Sync Issues
**Goal:** Detailed packet analysis

```bash
# Build firmware with JSON logging
pio run -e tbeam -t upload ENABLE_JSON_LOGGING=1

# Monitor with JSON parsing
python3 meshtastic_time_monitor.py /dev/ttyUSB0 --json --threshold 30
# Provides more detailed packet information
```

### Case 5: Monitor Embedded Node via TCP
**Goal:** Monitor a Raspberry Pi or Linux node running meshtasticd

```bash
# Connect to local meshtasticd
python3 meshtastic_time_monitor.py --tcp localhost --threshold 60

# Connect to remote node on network
python3 meshtastic_time_monitor.py --tcp 192.168.1.100 --threshold 60
```

### Case 6: Automatic Alerts to Admin Channel
**Goal:** Send alerts to admin channel when bad time detected

```bash
# Monitor and alert to channel 2 (admin channel)
python3 meshtastic_time_monitor.py /dev/ttyUSB0 \
  --alert \
  --alert-channel 2 \
  --alert-cooldown 3600 \
  --threshold 60

# Or via TCP
python3 meshtastic_time_monitor.py --tcp localhost \
  --alert \
  --alert-channel 2 \
  --alert-once
```

## New Features

### TCP Connection
Connect to embedded nodes running meshtasticd (Linux/Portduino):
```bash
python3 meshtastic_time_monitor.py --tcp <hostname> [--tcp-port 4403]
```

### Automatic Alerts
Send messages to mesh when bad time detected:
```bash
python3 meshtastic_time_monitor.py <port|--tcp host> --alert [options]
```

**Alert Options:**
- `--alert-channel N` - Send alerts to channel N (default: 0)
- `--alert-cooldown SECS` - Min seconds between alerts (default: 3600)
- `--alert-once` - Only alert once per node
- `--alert-message "MSG"` - Custom message format

**See [TCP_AND_ALERTING_GUIDE.md](TCP_AND_ALERTING_GUIDE.md) for complete details.**

## Tips

1. **Best Time to Monitor:** During regular position broadcasts (every 15-30 minutes)
2. **Sample Size:** Let it run for at least 5-10 minutes to get good data
3. **Multiple Nodes:** Connect to different nodes to cross-verify
4. **GPS Nodes:** Most accurate, use as reference
5. **Mesh-Only Nodes:** May have cascading errors if all nodes have bad time

## Reference: Time Quality Sources

| Quality Level | Source | Accuracy | Notes |
|--------------|--------|----------|-------|
| RTCQualityGPS | GPS satellite | ~1s | Best, requires GPS lock |
| RTCQualityNTP | Phone/NTP server | ~5s | Good, requires connectivity |
| RTCQualityFromNet | Other mesh nodes | Variable | Depends on source quality |
| RTCQualityDevice | Hardware RTC | Variable | Drifts over time |
| RTCQualityNone | Not set | N/A | No time available |
