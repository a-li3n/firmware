# TCP Connection and Alerting Guide

## New Features

The Meshtastic Time Monitor now supports:

1. **TCP connections** - Connect to embedded meshtasticd nodes over TCP port 4403
2. **Automatic alerts** - Send messages to the mesh when nodes with bad time are detected

## Installation

```bash
# Install required dependencies
pip3 install pyserial meshtastic
```

**Note:** The `meshtastic` library is only required if you want to use the `--alert` feature.

## TCP Connection Support

### What is TCP Mode?

TCP mode allows you to connect to Meshtastic nodes running `meshtasticd` (the Meshtastic daemon on Linux/Portduino platforms). This is useful for:

- Raspberry Pi nodes running meshtasticd
- Native Linux builds of Meshtastic
- Remote monitoring of nodes on your network
- Embedded systems without direct serial access

### Default Port

Meshtasticd listens on TCP port **4403** by default.

### Usage Examples

#### Connect to Local meshtasticd

```bash
# Connect to localhost (default port 4403)
python3 meshtastic_time_monitor.py --tcp localhost

# Same as above (explicit port)
python3 meshtastic_time_monitor.py --tcp localhost --tcp-port 4403
```

#### Connect to Remote Node

```bash
# Connect to node on your network
python3 meshtastic_time_monitor.py --tcp 192.168.1.100

# Connect to remote node with custom port
python3 meshtastic_time_monitor.py --tcp 192.168.1.50 --tcp-port 4403
```

#### TCP with Other Options

```bash
# TCP with JSON logging
python3 meshtastic_time_monitor.py --tcp localhost --json

# TCP with custom threshold
python3 meshtastic_time_monitor.py --tcp 192.168.1.100 --threshold 60

# TCP with all options
python3 meshtastic_time_monitor.py --tcp localhost --json --threshold 30 --stats-interval 120
```

### Setting Up meshtasticd

If you don't have meshtasticd running yet:

```bash
# Install meshtasticd (Linux)
pip3 install meshtastic

# Run meshtasticd
meshtasticd

# Or run on specific port
meshtasticd --port 4403

# Run in background
nohup meshtasticd &
```

### Connecting to TCP

When you connect via TCP, you'll see:

```
[+] Connected to localhost:4403 via TCP
[+] Meshtastic API interface initialized for messaging
[+] Monitoring for time synchronization issues (threshold: 30s)
[+] Press Ctrl+C to stop and show statistics
```

## Automatic Alerting

### What is Alerting?

When enabled, the monitor will automatically send a message to a designated channel on the mesh network when it detects a node sending incorrect time.

### Basic Alert Usage

```bash
# Enable alerts (default channel 0)
python3 meshtastic_time_monitor.py /dev/ttyUSB0 --alert

# Enable alerts on specific channel
python3 meshtastic_time_monitor.py /dev/ttyUSB0 --alert --alert-channel 2
```

### Alert Options

#### Alert Cooldown

Prevent spam by setting a minimum time between alerts for the same node:

```bash
# Default: 1 hour (3600 seconds) between alerts per node
python3 meshtastic_time_monitor.py /dev/ttyUSB0 --alert

# Custom cooldown: 30 minutes
python3 meshtastic_time_monitor.py /dev/ttyUSB0 --alert --alert-cooldown 1800

# Short cooldown: 5 minutes (for testing)
python3 meshtastic_time_monitor.py /dev/ttyUSB0 --alert --alert-cooldown 300
```

#### Alert Once Only

Only alert the first time a node is detected (never alert again for that node):

```bash
python3 meshtastic_time_monitor.py /dev/ttyUSB0 --alert --alert-once
```

#### Custom Alert Message

Customize the alert message sent to the mesh:

```bash
# Custom message with placeholders
python3 meshtastic_time_monitor.py /dev/ttyUSB0 --alert \
  --alert-message "WARNING: Node {node_id} time is off by {time_diff}"

# Simple message
python3 meshtastic_time_monitor.py /dev/ttyUSB0 --alert \
  --alert-message "Time sync issue detected on {node_id}"

# With time in seconds
python3 meshtastic_time_monitor.py /dev/ttyUSB0 --alert \
  --alert-message "Node {node_id} off by {time_diff_seconds}s"
```

**Available placeholders:**
- `{node_id}` - Node hex ID (e.g., 0x12345678)
- `{time_diff}` - Human-readable time difference (e.g., 2h 15m)
- `{time_diff_seconds}` - Time difference in seconds (e.g., 8100)

### Alert Channels

Channels in Meshtastic are numbered 0-7. Choose which channel receives the alerts:

```bash
# Channel 0 (default/primary)
python3 meshtastic_time_monitor.py /dev/ttyUSB0 --alert --alert-channel 0

# Channel 1
python3 meshtastic_time_monitor.py /dev/ttyUSB0 --alert --alert-channel 1

# Admin/monitoring channel (channel 2)
python3 meshtastic_time_monitor.py /dev/ttyUSB0 --alert --alert-channel 2
```

### Complete Examples

#### Example 1: Production Monitoring with Alerts

```bash
# Monitor via TCP, send alerts to admin channel with 2-hour cooldown
python3 meshtastic_time_monitor.py --tcp localhost \
  --alert \
  --alert-channel 2 \
  --alert-cooldown 7200 \
  --threshold 60 \
  --stats-interval 300
```

This will:
- Connect to local meshtasticd
- Alert on channel 2 (admin channel)
- Wait 2 hours before re-alerting about same node
- Only flag nodes off by more than 60 seconds
- Print statistics every 5 minutes

#### Example 2: Testing Setup

```bash
# Test alerting with short intervals
python3 meshtastic_time_monitor.py /dev/ttyUSB0 \
  --alert \
  --alert-channel 0 \
  --alert-cooldown 60 \
  --threshold 10 \
  --json
```

This will:
- Connect via serial
- Alert on primary channel
- Re-alert after just 60 seconds (for testing)
- Use strict 10-second threshold
- Parse JSON logs (more detailed)

#### Example 3: Silent Monitoring, Alert Once

```bash
# Monitor network, alert about each bad node only once
python3 meshtastic_time_monitor.py --tcp 192.168.1.100 \
  --alert \
  --alert-once \
  --alert-channel 1 \
  --alert-message "⚠️ {node_id} needs time sync! Off by {time_diff}" \
  --threshold 300
```

This will:
- Connect to remote node
- Alert each bad node only once (never repeat)
- Send to channel 1
- Custom message with warning emoji
- Only flag nodes off by more than 5 minutes

## Output Examples

### With Alerting Enabled

```
[+] Connected to /dev/ttyUSB0 at 115200 baud
[+] Meshtastic API interface initialized for messaging
[+] Monitoring for time synchronization issues (threshold: 30s)
[+] Alerts enabled on channel 0 (cooldown: 3600s)
[+] Press Ctrl+C to stop and show statistics

✓ OK Node 0x87654321: Reported: 2026-01-10 18:30:45 UTC, Diff: 2s

❌ INCORRECT Node 0x12345678: Reported: 2025-12-25 12:00:00 UTC, Diff: 15d 6h
  └─ WARNING: Time difference exceeds threshold!
[!] Sending alert to channel 0: ⚠️ Node 0x12345678 has incorrect time (off by 15d 6h)
  └─ Alert sent to channel 0

✓ OK Node 0xabcdef00: Reported: 2026-01-10 18:30:50 UTC, Diff: 5s

❌ INCORRECT Node 0x12345678: Reported: 2025-12-25 12:01:30 UTC, Diff: 15d 6h
  └─ WARNING: Time difference exceeds threshold!
  └─ Alert skipped (cooldown active)
```

### TCP Connection Output

```
[+] Connected to 192.168.1.100:4403 via TCP
[+] Meshtastic API interface initialized for messaging
[+] Monitoring for time synchronization issues (threshold: 60s)
[+] Alerts enabled on channel 2 (cooldown: 1800s)
[+] Press Ctrl+C to stop and show statistics

✓ OK Node 0x11223344: Reported: 2026-01-10 18:35:10 UTC, Diff: 3s
```

### Final Statistics with Alerts

```
======================================================================
FINAL STATISTICS
======================================================================

❌ NODES WITH INCORRECT TIME (1):

  Node: 0x12345678 [ALERTED]
    Samples: 12
    Average diff: 15d 6h
    Max diff: 15d 7h
    Last reported: 2025-12-25 12:10:45 UTC

✓ NODES WITH CORRECT TIME (3):
  0x87654321: avg diff 2s, 45 samples
  0xabcdef00: avg diff 4s, 32 samples
  0x11223344: avg diff 3s, 28 samples
======================================================================
```

The `[ALERTED]` tag shows which nodes had alerts sent about them.

## Troubleshooting

### TCP Connection Issues

#### "Connection refused"

```
[-] Failed to connect to localhost:4403: [Errno 61] Connection refused
```

**Solutions:**
1. Check if meshtasticd is running: `ps aux | grep meshtasticd`
2. Start meshtasticd: `meshtasticd &`
3. Check the port: `netstat -an | grep 4403`

#### "No route to host"

```
[-] Failed to connect to 192.168.1.100:4403: No route to host
```

**Solutions:**
1. Verify node IP address: `ping 192.168.1.100`
2. Check node is on same network
3. Verify firewall allows port 4403
4. Check meshtasticd is listening on 0.0.0.0, not just 127.0.0.1

#### "Connection timeout"

**Solutions:**
1. Node may be offline or unreachable
2. Wrong IP address
3. Firewall blocking connection
4. meshtasticd not running on remote node

### Alert Issues

#### "meshtastic library not found"

```
[-] Error: --alert requires 'meshtastic' library
    Install with: pip3 install meshtastic
```

**Solution:**
```bash
pip3 install meshtastic
```

#### "Could not initialize Meshtastic API (alerts disabled)"

```
[!] Warning: Could not initialize Meshtastic API (alerts disabled): ...
```

**Common causes:**
1. Another program is using the serial port
2. Permissions issue accessing serial port
3. Invalid port specified

**Solutions:**
```bash
# Close other programs using the port
pkill meshtastic

# Fix permissions
sudo usermod -a -G dialout $USER
# Then log out and back in

# For TCP, ensure meshtasticd is running properly
meshtasticd --version
```

#### Alerts not appearing on mesh

**Checklist:**
1. Verify channel index is correct (0-7)
2. Ensure your node has network connectivity
3. Check channel settings allow TX
4. Verify you're monitoring the right channel in your app
5. Check for encryption/channel mismatch

## Use Cases

### Case 1: Raspberry Pi Monitoring Node

**Scenario:** Dedicated RPi running meshtasticd to monitor mesh network

**Setup:**
```bash
# On Raspberry Pi, install meshtasticd
pip3 install meshtastic
meshtasticd &

# Create systemd service for monitoring (optional)
sudo nano /etc/systemd/system/mesh-time-monitor.service
```

**Service file:**
```ini
[Unit]
Description=Meshtastic Time Monitor
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi
ExecStart=/usr/bin/python3 /home/pi/meshtastic_time_monitor.py --tcp localhost --alert --alert-channel 2 --alert-cooldown 7200 --threshold 60
Restart=always

[Install]
WantedBy=multi-user.target
```

**Enable:**
```bash
sudo systemctl enable mesh-time-monitor
sudo systemctl start mesh-time-monitor
```

### Case 2: Remote Network Monitoring

**Scenario:** Monitor multiple nodes across your network

**Setup script (monitor_all.sh):**
```bash
#!/bin/bash
# Monitor multiple nodes in parallel

python3 meshtastic_time_monitor.py --tcp 192.168.1.100 --alert --alert-channel 2 > node1.log 2>&1 &
python3 meshtastic_time_monitor.py --tcp 192.168.1.101 --alert --alert-channel 2 > node2.log 2>&1 &
python3 meshtastic_time_monitor.py --tcp 192.168.1.102 --alert --alert-channel 2 > node3.log 2>&1 &

echo "Monitoring nodes 100, 101, 102..."
echo "Logs: node1.log, node2.log, node3.log"
```

### Case 3: Admin Channel Alerts

**Scenario:** Separate admin channel for system alerts

**Configuration:**
1. Create channel 2 as "Admin" in your Meshtastic app
2. Configure it for admins only
3. Run monitor sending alerts to channel 2

**Command:**
```bash
python3 meshtastic_time_monitor.py /dev/ttyUSB0 \
  --alert \
  --alert-channel 2 \
  --alert-message "ADMIN: Node {node_id} time drift {time_diff}" \
  --alert-cooldown 3600 \
  --threshold 120
```

## Best Practices

### Alert Channel Selection

- **Channel 0 (Primary)**: Good for general notifications everyone should see
- **Channel 1-3**: Use dedicated channel for monitoring/admin
- **Don't spam**: Use appropriate cooldown (1-2 hours for production)

### Threshold Selection

- **30-60 seconds**: Good for GPS-equipped networks
- **120-300 seconds**: Reasonable for mesh-only sync
- **10 seconds**: Strict, only for testing or high-accuracy requirements

### Cooldown Guidelines

- **Production**: 3600-7200 seconds (1-2 hours)
- **Testing**: 300-600 seconds (5-10 minutes)
- **One-time**: Use `--alert-once` for initial network setup

### Message Format

Keep messages short (Meshtastic has ~230 byte limit per message):

```bash
# Good - short and clear
--alert-message "⚠️ {node_id} time off {time_diff}"

# Bad - too verbose
--alert-message "WARNING: The node with ID {node_id} has been detected to have incorrect time synchronization with a difference of {time_diff}"
```

## Advanced Configuration

### Run as Background Service

```bash
# Run in background with nohup
nohup python3 meshtastic_time_monitor.py --tcp localhost --alert \
  --alert-channel 2 > time_monitor.log 2>&1 &

# Check it's running
ps aux | grep meshtastic_time_monitor

# View logs
tail -f time_monitor.log

# Stop
pkill -f meshtastic_time_monitor
```

### Multiple Monitors

Run multiple monitors for redundancy or different alert configs:

```bash
# Primary monitor (strict, admin channel)
python3 meshtastic_time_monitor.py --tcp localhost \
  --alert --alert-channel 2 --threshold 30 &

# Secondary monitor (relaxed, main channel)
python3 meshtastic_time_monitor.py --tcp localhost \
  --alert --alert-channel 0 --threshold 300 &
```

### Logging to File

```bash
# Save all output to file
python3 meshtastic_time_monitor.py --tcp localhost --alert \
  2>&1 | tee time_monitor_$(date +%Y%m%d).log
```

## Security Considerations

### Network Security

- TCP connection is **not encrypted** by default
- Don't expose port 4403 to the internet
- Use firewall rules to restrict access:

```bash
# Allow only local network
sudo ufw allow from 192.168.1.0/24 to any port 4403
```

### Alert Spam Prevention

- **Always use cooldown** in production to prevent alert spam
- Consider rate limiting alerts per hour
- Use `--alert-once` for setup/testing phases

### Channel Permissions

- Use role-based channels for admin alerts
- Don't send time alerts to public/encrypted channels unnecessarily
- Consider privacy when exposing node IDs in alerts

## FAQ

**Q: Can I use both serial and TCP at the same time?**
A: No, choose one connection method per monitor instance. But you can run multiple instances.

**Q: Will alerts work without the meshtastic library?**
A: No, the meshtastic library is required for sending messages.

**Q: Can I alert via MQTT instead of mesh?**
A: Not currently. The script only supports direct mesh messaging.

**Q: How many alerts can be sent?**
A: Limited by mesh bandwidth. Use appropriate cooldowns to prevent network congestion.

**Q: Can I customize alert format per node?**
A: Not currently. All alerts use the same format template.

**Q: Does alerting work with encrypted channels?**
A: Yes, if your node has the encryption key for that channel.

## Summary

### TCP Connection Commands

```bash
# Local
python3 meshtastic_time_monitor.py --tcp localhost

# Remote
python3 meshtastic_time_monitor.py --tcp 192.168.1.100

# Custom port
python3 meshtastic_time_monitor.py --tcp localhost --tcp-port 4403
```

### Alert Commands

```bash
# Basic alert
python3 meshtastic_time_monitor.py /dev/ttyUSB0 --alert

# Custom channel and cooldown
python3 meshtastic_time_monitor.py /dev/ttyUSB0 --alert --alert-channel 2 --alert-cooldown 3600

# Alert once only
python3 meshtastic_time_monitor.py /dev/ttyUSB0 --alert --alert-once

# Custom message
python3 meshtastic_time_monitor.py /dev/ttyUSB0 --alert --alert-message "Node {node_id} off by {time_diff}"
```

### Combined TCP + Alerts

```bash
python3 meshtastic_time_monitor.py --tcp localhost \
  --alert \
  --alert-channel 2 \
  --alert-cooldown 3600 \
  --threshold 60 \
  --json
```
