# Meshtastic Time Monitor - Complete Guide

A comprehensive monitoring tool for tracking time synchronization across Meshtastic mesh networks with support for serial connections, TCP connections (embedded nodes), and automatic mesh alerts.

## Features

✅ **Serial Connection** - Monitor via USB/serial port
✅ **TCP Connection** - Monitor embedded nodes running meshtasticd (port 4403)
✅ **Automatic Alerts** - Send messages to mesh when bad time detected
✅ **Real-time Monitoring** - See time updates as they happen
✅ **Statistics** - Periodic summaries and final reports
✅ **Configurable Thresholds** - Set acceptable time difference
✅ **Alert Cooldown** - Prevent message spam with configurable cooldowns
✅ **Custom Messages** - Customize alert message format
✅ **JSON Support** - Parse JSON-formatted logs (ENABLE_JSON_LOGGING builds)

## Quick Start

### Installation

```bash
# Install dependencies
pip3 install pyserial meshtastic
```

### Basic Usage

```bash
# Serial connection
python3 meshtastic_time_monitor.py /dev/ttyUSB0

# TCP connection (embedded nodes)
python3 meshtastic_time_monitor.py --tcp localhost

# With automatic alerts
python3 meshtastic_time_monitor.py /dev/ttyUSB0 --alert --alert-channel 2
```

## Connection Methods

### Serial Connection (USB)

For nodes connected via USB:

```bash
python3 meshtastic_time_monitor.py /dev/ttyUSB0
python3 meshtastic_time_monitor.py COM3  # Windows
```

### TCP Connection (Embedded Nodes)

For Raspberry Pi, Linux, or Portduino nodes running meshtasticd:

```bash
# Local node
python3 meshtastic_time_monitor.py --tcp localhost

# Remote node on network
python3 meshtastic_time_monitor.py --tcp 192.168.1.100

# Custom TCP port
python3 meshtastic_time_monitor.py --tcp localhost --tcp-port 4403
```

**Default TCP port:** 4403

## Alert System

### Enable Alerts

```bash
# Basic alert to channel 0
python3 meshtastic_time_monitor.py /dev/ttyUSB0 --alert

# Alert to specific channel
python3 meshtastic_time_monitor.py /dev/ttyUSB0 --alert --alert-channel 2

# Alert once per node (no repeats)
python3 meshtastic_time_monitor.py /dev/ttyUSB0 --alert --alert-once

# Custom cooldown (30 minutes)
python3 meshtastic_time_monitor.py /dev/ttyUSB0 --alert --alert-cooldown 1800
```

### Alert Options

| Option | Description | Default |
|--------|-------------|---------|
| `--alert` | Enable alerts | Disabled |
| `--alert-channel N` | Send alerts to channel N | 0 |
| `--alert-cooldown SECS` | Min seconds between alerts per node | 3600 (1 hour) |
| `--alert-once` | Alert only once per node | False |
| `--alert-message "MSG"` | Custom alert format | See below |

### Custom Alert Messages

```bash
# Default message
"⚠️ Node {node_id} has incorrect time (off by {time_diff})"

# Custom examples
python3 meshtastic_time_monitor.py /dev/ttyUSB0 --alert \
  --alert-message "WARNING: {node_id} time off by {time_diff}"

python3 meshtastic_time_monitor.py /dev/ttyUSB0 --alert \
  --alert-message "Node {node_id} drift: {time_diff_seconds}s"
```

**Available placeholders:**
- `{node_id}` - Node hex ID (e.g., 0x12345678)
- `{time_diff}` - Human-readable (e.g., 2h 15m)
- `{time_diff_seconds}` - Seconds (e.g., 8100)

## Command-Line Options

### Connection Options

```bash
# Serial
<port>                    # Serial port path
--baud RATE              # Baud rate (default: 115200)

# TCP
--tcp HOST               # TCP hostname/IP
--tcp-port PORT          # TCP port (default: 4403)
```

### Monitoring Options

```bash
--threshold SECS         # Time difference threshold (default: 30)
--json                   # Parse JSON logs
--stats-interval SECS    # Statistics interval (default: 60)
```

### Alert Options

```bash
--alert                  # Enable alerts
--alert-channel N        # Alert channel (default: 0)
--alert-cooldown SECS    # Alert cooldown (default: 3600)
--alert-once             # Alert only once per node
--alert-message "MSG"    # Custom message format
```

## Usage Examples

### Example 1: Basic Serial Monitoring

```bash
python3 meshtastic_time_monitor.py /dev/ttyUSB0 --threshold 30
```

Monitor connected node, flag nodes off by more than 30 seconds.

### Example 2: TCP with Alerts

```bash
python3 meshtastic_time_monitor.py --tcp localhost \
  --alert \
  --alert-channel 2 \
  --alert-cooldown 3600 \
  --threshold 60
```

Monitor local meshtasticd, send alerts to channel 2, wait 1 hour between alerts.

### Example 3: Remote Node Monitoring

```bash
python3 meshtastic_time_monitor.py --tcp 192.168.1.100 \
  --json \
  --threshold 120
```

Monitor remote node with JSON logs, 2-minute threshold.

### Example 4: Strict Monitoring with Immediate Alerts

```bash
python3 meshtastic_time_monitor.py /dev/ttyUSB0 \
  --alert \
  --alert-channel 0 \
  --alert-once \
  --threshold 10
```

Strict 10-second threshold, alert once per bad node on primary channel.

### Example 5: Production Monitoring Setup

```bash
python3 meshtastic_time_monitor.py --tcp localhost \
  --alert \
  --alert-channel 2 \
  --alert-cooldown 7200 \
  --threshold 60 \
  --stats-interval 300 \
  --json
```

Full-featured monitoring: TCP connection, admin channel alerts (every 2 hours), 1-minute threshold, 5-minute stats, JSON parsing.

## Output Examples

### Without Alerts

```
[+] Connected to /dev/ttyUSB0 at 115200 baud
[+] Monitoring for time synchronization issues (threshold: 30s)

✓ OK Node 0x87654321: Reported: 2026-01-10 18:30:45 UTC, Diff: 2s
❌ INCORRECT Node 0x12345678: Reported: 2025-12-25 12:00:00 UTC, Diff: 15d 6h
  └─ WARNING: Time difference exceeds threshold!
✓ OK Node 0xabcdef00: Reported: 2026-01-10 18:30:50 UTC, Diff: 5s
```

### With Alerts

```
[+] Connected to localhost:4403 via TCP
[+] Meshtastic API interface initialized for messaging
[+] Alerts enabled on channel 2 (cooldown: 3600s)

✓ OK Node 0x87654321: Reported: 2026-01-10 18:30:45 UTC, Diff: 2s

❌ INCORRECT Node 0x12345678: Reported: 2025-12-25 12:00:00 UTC, Diff: 15d 6h
  └─ WARNING: Time difference exceeds threshold!
[!] Sending alert to channel 2: ⚠️ Node 0x12345678 has incorrect time (off by 15d 6h)
  └─ Alert sent to channel 2

✓ OK Node 0xabcdef00: Reported: 2026-01-10 18:30:50 UTC, Diff: 5s
```

## How It Works

### Time in Meshtastic

Meshtastic uses a quality hierarchy for time sources:

1. **GPS** (RTCQualityGPS) - Most accurate (~1s)
2. **NTP/Phone** (RTCQualityNTP) - Very accurate (~5s)
3. **Mesh Network** (RTCQualityFromNet) - Depends on source
4. **Hardware RTC** (RTCQualityDevice) - Drifts over time
5. **None** (RTCQualityNone) - No time set

Position messages include a `time` field (Unix timestamp) that nodes use to sync their clocks.

### What the Monitor Does

1. Connects via serial or TCP
2. Parses Position messages from mesh packets
3. Compares reported time to system time
4. Identifies nodes beyond threshold
5. Optionally sends alerts to mesh
6. Tracks statistics and generates reports

## Documentation

- **[QUICK_START_TIME_MONITOR.md](QUICK_START_TIME_MONITOR.md)** - Quick reference
- **[TIME_MONITOR_README.md](TIME_MONITOR_README.md)** - Detailed documentation
- **[TCP_AND_ALERTING_GUIDE.md](TCP_AND_ALERTING_GUIDE.md)** - TCP & alert features
- **[TIME_MONITORING_SUMMARY.md](TIME_MONITORING_SUMMARY.md)** - Complete overview
- **[example_serial_output.txt](example_serial_output.txt)** - Sample output

## Troubleshooting

### TCP Connection Issues

**"Connection refused"**
```bash
# Check meshtasticd is running
ps aux | grep meshtasticd

# Start it if needed
meshtasticd &
```

**"Cannot import meshtastic"**
```bash
pip3 install meshtastic
```

### Serial Connection Issues

**"Permission denied"**
```bash
# Linux/Mac
sudo usermod -a -G dialout $USER
# Then log out and back in
```

**"No such file or directory"**
```bash
# Find correct port
ls /dev/tty* | grep -i usb
```

### Alert Issues

**Alerts not working**
- Ensure `meshtastic` library installed: `pip3 install meshtastic`
- Check channel index is correct (0-7)
- Verify your node has mesh connectivity
- Ensure channel allows TX

## Advanced Usage

### Run as Background Service

```bash
# Run in background
nohup python3 meshtastic_time_monitor.py --tcp localhost --alert \
  --alert-channel 2 > time_monitor.log 2>&1 &

# Check it's running
ps aux | grep meshtastic_time_monitor

# View logs
tail -f time_monitor.log
```

### Systemd Service (Linux)

Create `/etc/systemd/system/mesh-time-monitor.service`:

```ini
[Unit]
Description=Meshtastic Time Monitor
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi
ExecStart=/usr/bin/python3 /home/pi/meshtastic_time_monitor.py --tcp localhost --alert --alert-channel 2
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable mesh-time-monitor
sudo systemctl start mesh-time-monitor
sudo systemctl status mesh-time-monitor
```

## Use Cases

### Case 1: Find Nodes with Bad Time

```bash
python3 meshtastic_time_monitor.py /dev/ttyUSB0 --threshold 60
# Run for 10-15 minutes
# Press Ctrl+C to see final report
```

### Case 2: Monitor Embedded Node

```bash
# Raspberry Pi running meshtasticd
python3 meshtastic_time_monitor.py --tcp localhost --threshold 60
```

### Case 3: Automated Network Monitoring

```bash
# Send alerts to admin channel when issues detected
python3 meshtastic_time_monitor.py --tcp localhost \
  --alert --alert-channel 2 --alert-cooldown 3600 --threshold 60
```

### Case 4: Multi-Node Monitoring

```bash
# Monitor multiple nodes (run in parallel)
python3 meshtastic_time_monitor.py --tcp 192.168.1.100 --alert > node1.log &
python3 meshtastic_time_monitor.py --tcp 192.168.1.101 --alert > node2.log &
python3 meshtastic_time_monitor.py --tcp 192.168.1.102 --alert > node3.log &
```

## Best Practices

1. **Choose appropriate threshold**
   - GPS networks: 30-60 seconds
   - Mesh-only: 120-300 seconds

2. **Use alert cooldown**
   - Production: 3600-7200 seconds (1-2 hours)
   - Testing: 300-600 seconds (5-10 minutes)

3. **Dedicated admin channel**
   - Use channel 2 or 3 for monitoring alerts
   - Keeps primary channel clean

4. **Monitor sample size**
   - Run for at least 10-15 minutes
   - Multiple position broadcasts needed

5. **Security**
   - Don't expose TCP port 4403 to internet
   - Use firewall rules for TCP connections

## License

This tool is provided as-is for monitoring Meshtastic devices.

## Contributing

Issues and improvements welcome!

## See Also

- [Meshtastic Documentation](https://meshtastic.org/docs/)
- [Meshtastic Firmware](https://github.com/meshtastic/firmware)
- [Meshtastic Python CLI](https://github.com/meshtastic/python)
