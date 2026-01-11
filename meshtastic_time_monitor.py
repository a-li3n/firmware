#!/usr/bin/env python3
"""
Meshtastic Time Monitor

This script monitors serial/TCP output from a Meshtastic node and tracks which remote nodes
are sending time information to the mesh, identifying nodes with incorrect time.

Usage:
    # Serial connection
    python3 meshtastic_time_monitor.py /dev/ttyUSB0
    python3 meshtastic_time_monitor.py /dev/ttyUSB0 --threshold 60 --json

    # TCP connection (for embedded meshtasticd nodes)
    python3 meshtastic_time_monitor.py --tcp localhost
    python3 meshtastic_time_monitor.py --tcp 192.168.1.100 --port 4403

    # With alerting
    python3 meshtastic_time_monitor.py /dev/ttyUSB0 --alert --alert-channel 0
    python3 meshtastic_time_monitor.py --tcp localhost --alert --alert-cooldown 3600
"""

import serial
import socket
import re
import json
import time
import argparse
import sys
from datetime import datetime, timezone
from collections import defaultdict
from typing import Dict, Optional, Tuple, Set

try:
    import meshtastic
    import meshtastic.serial_interface
    import meshtastic.tcp_interface
    MESHTASTIC_AVAILABLE = True
except ImportError:
    MESHTASTIC_AVAILABLE = False


class TimeTracker:
    """Tracks time information from mesh nodes."""

    def __init__(self, time_threshold_seconds: int = 30):
        """
        Initialize the time tracker.

        Args:
            time_threshold_seconds: Maximum acceptable time difference in seconds
        """
        self.time_threshold = time_threshold_seconds
        self.node_times: Dict[str, list] = defaultdict(list)  # node_id -> [(timestamp, reported_time, local_time)]
        self.node_names: Dict[str, str] = {}  # node_id -> node_name
        self.alerted_nodes: Set[str] = set()  # nodes we've already alerted about
        self.last_alert_time: Dict[str, float] = {}  # node_id -> last alert timestamp

    def update_node_time(self, node_id: str, reported_time: int, node_name: Optional[str] = None) -> Tuple[bool, int]:
        """
        Update time information for a node.

        Args:
            node_id: Node identifier (hex format like 0x12345678)
            reported_time: Time reported by the node (seconds since epoch)
            node_name: Optional human-readable name for the node

        Returns:
            Tuple of (is_incorrect, time_difference_seconds)
        """
        local_time = int(time.time())
        time_diff = abs(reported_time - local_time)

        self.node_times[node_id].append({
            'timestamp': local_time,
            'reported_time': reported_time,
            'time_diff': time_diff
        })

        if node_name:
            self.node_names[node_id] = node_name

        is_incorrect = time_diff > self.time_threshold
        return is_incorrect, time_diff

    def should_alert(self, node_id: str, cooldown_seconds: int = 3600) -> bool:
        """
        Determine if we should send an alert for this node.

        Args:
            node_id: Node identifier
            cooldown_seconds: Minimum time between alerts for same node

        Returns:
            True if alert should be sent
        """
        current_time = time.time()

        # Check if we've alerted recently
        if node_id in self.last_alert_time:
            time_since_last_alert = current_time - self.last_alert_time[node_id]
            if time_since_last_alert < cooldown_seconds:
                return False

        return True

    def mark_alerted(self, node_id: str):
        """Mark that we've sent an alert for this node."""
        self.alerted_nodes.add(node_id)
        self.last_alert_time[node_id] = time.time()

    def get_node_name(self, node_id: str) -> str:
        """Get the human-readable name for a node, if available."""
        return self.node_names.get(node_id, node_id)

    def get_statistics(self) -> Dict:
        """Get statistics about all tracked nodes."""
        stats = {}
        for node_id, times in self.node_times.items():
            if not times:
                continue

            time_diffs = [t['time_diff'] for t in times]
            stats[node_id] = {
                'name': self.get_node_name(node_id),
                'sample_count': len(times),
                'avg_diff': sum(time_diffs) / len(time_diffs),
                'max_diff': max(time_diffs),
                'min_diff': min(time_diffs),
                'last_seen': times[-1]['timestamp'],
                'last_reported_time': times[-1]['reported_time']
            }
        return stats


class MeshtasticConnection:
    """Base class for Meshtastic connections."""

    def connect(self) -> bool:
        raise NotImplementedError

    def disconnect(self):
        raise NotImplementedError

    def read_line(self) -> Optional[str]:
        raise NotImplementedError

    def send_message(self, text: str, channel: int = 0) -> bool:
        raise NotImplementedError


class SerialConnection(MeshtasticConnection):
    """Serial connection to Meshtastic device."""

    def __init__(self, port: str, baudrate: int = 115200):
        self.port = port
        self.baudrate = baudrate
        self.serial = None
        self.meshtastic_interface = None

    def connect(self) -> bool:
        try:
            self.serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=1
            )
            print(f"[+] Connected to {self.port} at {self.baudrate} baud")

            # Try to initialize Meshtastic interface for sending messages
            if MESHTASTIC_AVAILABLE:
                try:
                    self.meshtastic_interface = meshtastic.serial_interface.SerialInterface(self.port)
                    print(f"[+] Meshtastic API interface initialized for messaging")
                except Exception as e:
                    print(f"[!] Warning: Could not initialize Meshtastic API (alerts disabled): {e}")
                    self.meshtastic_interface = None

            time.sleep(2)  # Wait for connection to stabilize
            return True
        except serial.SerialException as e:
            print(f"[-] Failed to connect to {self.port}: {e}")
            return False

    def disconnect(self):
        if self.meshtastic_interface:
            try:
                self.meshtastic_interface.close()
            except:
                pass
        if self.serial and self.serial.is_open:
            self.serial.close()
            print(f"[+] Disconnected from {self.port}")

    def read_line(self) -> Optional[str]:
        if not self.serial or not self.serial.is_open:
            return None
        try:
            line = self.serial.readline()
            if line:
                return line.decode('utf-8', errors='ignore').strip()
        except Exception as e:
            print(f"[-] Serial read error: {e}")
            return None
        return None

    def send_message(self, text: str, channel: int = 0) -> bool:
        if not self.meshtastic_interface:
            return False
        try:
            self.meshtastic_interface.sendText(text, channelIndex=channel)
            return True
        except Exception as e:
            print(f"[-] Failed to send message: {e}")
            return False


class TCPConnection(MeshtasticConnection):
    """TCP connection to Meshtastic daemon (meshtasticd)."""

    def __init__(self, host: str = 'localhost', port: int = 4403):
        self.host = host
        self.port = port
        self.socket = None
        self.meshtastic_interface = None
        self.buffer = ""

    def connect(self) -> bool:
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(1.0)
            self.socket.connect((self.host, self.port))
            print(f"[+] Connected to {self.host}:{self.port} via TCP")

            # Try to initialize Meshtastic interface for sending messages
            if MESHTASTIC_AVAILABLE:
                try:
                    self.meshtastic_interface = meshtastic.tcp_interface.TCPInterface(hostname=self.host)
                    print(f"[+] Meshtastic API interface initialized for messaging")
                except Exception as e:
                    print(f"[!] Warning: Could not initialize Meshtastic API (alerts disabled): {e}")
                    self.meshtastic_interface = None

            return True
        except socket.error as e:
            print(f"[-] Failed to connect to {self.host}:{self.port}: {e}")
            return False

    def disconnect(self):
        if self.meshtastic_interface:
            try:
                self.meshtastic_interface.close()
            except:
                pass
        if self.socket:
            self.socket.close()
            print(f"[+] Disconnected from {self.host}:{self.port}")

    def read_line(self) -> Optional[str]:
        if not self.socket:
            return None

        try:
            # Read data from socket
            data = self.socket.recv(4096)
            if not data:
                return None

            # Add to buffer
            self.buffer += data.decode('utf-8', errors='ignore')

            # Extract complete lines
            if '\n' in self.buffer:
                lines = self.buffer.split('\n')
                self.buffer = lines[-1]  # Keep incomplete line in buffer
                if lines[0]:  # Return first complete line
                    return lines[0].strip()
        except socket.timeout:
            return None
        except Exception as e:
            print(f"[-] TCP read error: {e}")
            return None

        return None

    def send_message(self, text: str, channel: int = 0) -> bool:
        if not self.meshtastic_interface:
            return False
        try:
            self.meshtastic_interface.sendText(text, channelIndex=channel)
            return True
        except Exception as e:
            print(f"[-] Failed to send message: {e}")
            return False


class MeshtasticMonitor:
    """Monitor output from Meshtastic device."""

    def __init__(self, connection: MeshtasticConnection, use_json: bool = False):
        """
        Initialize the monitor.

        Args:
            connection: Connection object (Serial or TCP)
            use_json: Whether to parse JSON formatted logs
        """
        self.connection = connection
        self.use_json = use_json

        # Regex patterns for parsing text logs
        self.packet_pattern = re.compile(
            r'(id=0x([0-9a-fA-F]+)\s+fr=0x([0-9a-fA-F]+)\s+to=0x([0-9a-fA-F]+).*?'
            r'Portnum=(\d+).*?(?:rxtime=(\d+))?)'
        )
        self.position_pattern = re.compile(
            r'Position packet: time=(\d+) lat=(-?\d+) lon=(-?\d+)'
        )

    def connect(self):
        """Connect to the device."""
        return self.connection.connect()

    def disconnect(self):
        """Disconnect from the device."""
        self.connection.disconnect()

    def read_line(self) -> Optional[str]:
        """Read a line from the connection."""
        return self.connection.read_line()

    def send_alert(self, text: str, channel: int = 0) -> bool:
        """Send an alert message to the mesh."""
        return self.connection.send_message(text, channel)

    def parse_text_packet(self, line: str) -> Optional[Dict]:
        """Parse text-formatted packet log."""
        match = self.packet_pattern.search(line)
        if not match:
            return None

        packet_id = match.group(2)
        from_node = match.group(3)
        to_node = match.group(4)
        portnum = int(match.group(5))
        rx_time = int(match.group(6)) if match.group(6) else None

        return {
            'id': packet_id,
            'from': from_node,
            'to': to_node,
            'portnum': portnum,
            'rx_time': rx_time,
            'raw_line': line
        }

    def parse_position_log(self, line: str) -> Optional[Dict]:
        """Parse position packet log."""
        match = self.position_pattern.search(line)
        if not match:
            return None

        return {
            'time': int(match.group(1)),
            'lat': int(match.group(2)),
            'lon': int(match.group(3))
        }

    def parse_json_packet(self, line: str) -> Optional[Dict]:
        """Parse JSON-formatted packet log."""
        try:
            # Look for JSON in the line (may have prefix like "TRACE: ")
            json_start = line.find('{')
            if json_start == -1:
                return None

            json_str = line[json_start:]
            data = json.loads(json_str)

            # Extract relevant fields
            result = {}
            if 'from' in data:
                result['from'] = f"{data['from']:08x}"
            if 'to' in data:
                result['to'] = f"{data['to']:08x}"
            if 'id' in data:
                result['id'] = f"{data['id']:08x}"
            if 'rxTime' in data:
                result['rx_time'] = data['rxTime']
            if 'type' in data:
                result['type'] = data['type']
            if 'payload' in data:
                result['payload'] = data['payload']
                # Check for position data with time
                if isinstance(data['payload'], dict):
                    if 'time' in data['payload']:
                        result['position_time'] = data['payload']['time']
                    if 'latitude_i' in data['payload']:
                        result['lat'] = data['payload']['latitude_i']
                    if 'longitude_i' in data['payload']:
                        result['lon'] = data['payload']['longitude_i']

            return result
        except json.JSONDecodeError:
            return None
        except Exception as e:
            # Silently ignore malformed JSON
            return None


def format_timestamp(ts: int) -> str:
    """Format Unix timestamp as human-readable string."""
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')


def format_time_diff(seconds: int) -> str:
    """Format time difference as human-readable string."""
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes}m {secs}s"
    elif seconds < 86400:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours}h {minutes}m"
    else:
        days = seconds // 86400
        hours = (seconds % 86400) // 3600
        return f"{days}d {hours}h"


def send_bad_time_alert(monitor: MeshtasticMonitor, node_id: str, time_diff: int,
                        channel: int, message_format: str) -> bool:
    """
    Send an alert to the mesh about a node with bad time.

    Args:
        monitor: Monitor instance
        node_id: Node ID with bad time
        time_diff: Time difference in seconds
        channel: Channel to send alert to
        message_format: Format string for message

    Returns:
        True if message sent successfully
    """
    try:
        # Format the alert message
        message = message_format.format(
            node_id=node_id,
            time_diff=format_time_diff(time_diff),
            time_diff_seconds=time_diff
        )

        print(f"[!] Sending alert to channel {channel}: {message}")
        return monitor.send_alert(message, channel)
    except Exception as e:
        print(f"[-] Failed to send alert: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Monitor Meshtastic serial/TCP output for time synchronization issues'
    )

    # Connection options
    conn_group = parser.add_mutually_exclusive_group(required=True)
    conn_group.add_argument('port', nargs='?', help='Serial port (e.g., /dev/ttyUSB0 or COM3)')
    conn_group.add_argument('--tcp', metavar='HOST', help='TCP connection to meshtasticd (e.g., localhost or 192.168.1.100)')

    parser.add_argument('--tcp-port', type=int, default=4403, help='TCP port (default: 4403)')
    parser.add_argument('--baud', type=int, default=115200, help='Serial baud rate (default: 115200)')

    # Monitoring options
    parser.add_argument('--threshold', type=int, default=30,
                       help='Time difference threshold in seconds (default: 30)')
    parser.add_argument('--json', action='store_true',
                       help='Parse JSON formatted logs (for ENABLE_JSON_LOGGING builds)')
    parser.add_argument('--stats-interval', type=int, default=60,
                       help='Interval to print statistics in seconds (default: 60)')

    # Alert options
    parser.add_argument('--alert', action='store_true',
                       help='Send alerts to mesh when bad time detected')
    parser.add_argument('--alert-channel', type=int, default=0,
                       help='Channel to send alerts to (default: 0)')
    parser.add_argument('--alert-cooldown', type=int, default=3600,
                       help='Minimum seconds between alerts for same node (default: 3600)')
    parser.add_argument('--alert-message', type=str,
                       default='⚠️ Node {node_id} has incorrect time (off by {time_diff})',
                       help='Alert message format (use {node_id}, {time_diff}, {time_diff_seconds})')
    parser.add_argument('--alert-once', action='store_true',
                       help='Only alert once per node (ignore cooldown)')

    args = parser.parse_args()

    # Check for meshtastic library if alerts enabled
    if args.alert and not MESHTASTIC_AVAILABLE:
        print("[-] Error: --alert requires 'meshtastic' library")
        print("    Install with: pip3 install meshtastic")
        sys.exit(1)

    # Create connection
    if args.tcp:
        connection = TCPConnection(host=args.tcp, port=args.tcp_port)
    elif args.port:
        connection = SerialConnection(port=args.port, baudrate=args.baud)
    else:
        parser.print_help()
        sys.exit(1)

    # Initialize tracker and monitor
    tracker = TimeTracker(time_threshold_seconds=args.threshold)
    monitor = MeshtasticMonitor(connection=connection, use_json=args.json)

    # Connect
    if not monitor.connect():
        sys.exit(1)

    print(f"[+] Monitoring for time synchronization issues (threshold: {args.threshold}s)")
    if args.alert:
        print(f"[+] Alerts enabled on channel {args.alert_channel} "
              f"(cooldown: {args.alert_cooldown}s)" if not args.alert_once else "(one-time only)")
    print(f"[+] Press Ctrl+C to stop and show statistics\n")

    last_stats_time = time.time()

    try:
        while True:
            line = monitor.read_line()
            if not line:
                continue

            # Try parsing as JSON if enabled
            if args.json:
                packet = monitor.parse_json_packet(line)
                if packet and 'position_time' in packet:
                    from_node = f"0x{packet['from']}"
                    position_time = packet['position_time']

                    is_incorrect, time_diff = tracker.update_node_time(from_node, position_time)

                    status = "❌ INCORRECT" if is_incorrect else "✓ OK"
                    print(f"{status} Node {from_node}: "
                          f"Reported: {format_timestamp(position_time)}, "
                          f"Diff: {format_time_diff(time_diff)}")

                    if is_incorrect:
                        print(f"  └─ WARNING: Time difference exceeds threshold!")

                        # Send alert if enabled
                        if args.alert:
                            should_alert = tracker.should_alert(from_node, args.alert_cooldown if not args.alert_once else float('inf'))
                            if should_alert:
                                if send_bad_time_alert(monitor, from_node, time_diff,
                                                      args.alert_channel, args.alert_message):
                                    tracker.mark_alerted(from_node)
                                    print(f"  └─ Alert sent to channel {args.alert_channel}")

            # Try parsing text format
            else:
                # Look for Position packet logs
                position = monitor.parse_position_log(line)
                if position:
                    # Position logs don't include sender ID in this format
                    # We need to correlate with packet logs
                    # For now, just note that a position with time was seen
                    print(f"[INFO] Position update: time={format_timestamp(position['time'])}")

                # Parse general packet info
                packet = monitor.parse_text_packet(line)
                if packet:
                    # Check if this is a POSITION_APP packet (portnum=3)
                    if packet['portnum'] == 3 and packet['rx_time']:
                        from_node = f"0x{packet['from']}"

                        # Check subsequent lines for Position packet log
                        next_line = monitor.read_line()
                        if next_line:
                            position = monitor.parse_position_log(next_line)
                            if position:
                                is_incorrect, time_diff = tracker.update_node_time(
                                    from_node,
                                    position['time']
                                )

                                status = "❌ INCORRECT" if is_incorrect else "✓ OK"
                                print(f"{status} Node {from_node}: "
                                      f"Reported: {format_timestamp(position['time'])}, "
                                      f"Diff: {format_time_diff(time_diff)}")

                                if is_incorrect:
                                    print(f"  └─ WARNING: Time difference exceeds threshold!")

                                    # Send alert if enabled
                                    if args.alert:
                                        should_alert = tracker.should_alert(from_node, args.alert_cooldown if not args.alert_once else float('inf'))
                                        if should_alert:
                                            if send_bad_time_alert(monitor, from_node, time_diff,
                                                                  args.alert_channel, args.alert_message):
                                                tracker.mark_alerted(from_node)
                                                print(f"  └─ Alert sent to channel {args.alert_channel}")

            # Print periodic statistics
            current_time = time.time()
            if current_time - last_stats_time >= args.stats_interval:
                print("\n" + "="*70)
                print("STATISTICS SUMMARY")
                print("="*70)
                stats = tracker.get_statistics()

                if not stats:
                    print("No nodes tracked yet.")
                else:
                    for node_id, node_stats in sorted(stats.items()):
                        print(f"\nNode: {node_stats['name']}")
                        print(f"  Samples: {node_stats['sample_count']}")
                        print(f"  Average time diff: {format_time_diff(int(node_stats['avg_diff']))}")
                        print(f"  Max time diff: {format_time_diff(int(node_stats['max_diff']))}")
                        print(f"  Last seen: {format_timestamp(node_stats['last_seen'])}")
                        print(f"  Last reported time: {format_timestamp(node_stats['last_reported_time'])}")

                print("="*70 + "\n")
                last_stats_time = current_time

    except KeyboardInterrupt:
        print("\n\n[+] Stopping monitor...")

        # Print final statistics
        print("\n" + "="*70)
        print("FINAL STATISTICS")
        print("="*70)
        stats = tracker.get_statistics()

        if not stats:
            print("No nodes tracked.")
        else:
            # Sort by max time diff to show worst offenders first
            sorted_nodes = sorted(
                stats.items(),
                key=lambda x: x[1]['max_diff'],
                reverse=True
            )

            incorrect_nodes = []
            correct_nodes = []

            for node_id, node_stats in sorted_nodes:
                if node_stats['max_diff'] > args.threshold:
                    incorrect_nodes.append((node_id, node_stats))
                else:
                    correct_nodes.append((node_id, node_stats))

            if incorrect_nodes:
                print(f"\n❌ NODES WITH INCORRECT TIME ({len(incorrect_nodes)}):")
                for node_id, node_stats in incorrect_nodes:
                    alerted = " [ALERTED]" if node_id in tracker.alerted_nodes else ""
                    print(f"\n  Node: {node_stats['name']}{alerted}")
                    print(f"    Samples: {node_stats['sample_count']}")
                    print(f"    Average diff: {format_time_diff(int(node_stats['avg_diff']))}")
                    print(f"    Max diff: {format_time_diff(int(node_stats['max_diff']))}")
                    print(f"    Last reported: {format_timestamp(node_stats['last_reported_time'])}")

            if correct_nodes:
                print(f"\n✓ NODES WITH CORRECT TIME ({len(correct_nodes)}):")
                for node_id, node_stats in correct_nodes:
                    print(f"  {node_stats['name']}: "
                          f"avg diff {format_time_diff(int(node_stats['avg_diff']))}, "
                          f"{node_stats['sample_count']} samples")

        print("="*70)

    finally:
        monitor.disconnect()


if __name__ == '__main__':
    main()
