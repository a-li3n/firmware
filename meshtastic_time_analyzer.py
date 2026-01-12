#!/usr/bin/env python3
"""
Meshtastic Time Log Analyzer

This script analyzes existing Meshtastic log files (or journalctl output) to identify
nodes with time synchronization issues.

NOTE: By default, entries with time=0 (1970-01-01 00:00:00 UTC) are filtered out as they
      typically indicate uninitialized time values. Use --include-epoch-zero to include them.

Usage:
    # Analyze a log file
    python3 meshtastic_time_analyzer.py /var/log/meshtastic.log

    # Analyze from stdin (journalctl)
    journalctl -u meshtasticd -n 10000 | python3 meshtastic_time_analyzer.py -

    # Analyze with custom threshold
    python3 meshtastic_time_analyzer.py /var/log/meshtastic.log --threshold 60

    # Output as JSON
    python3 meshtastic_time_analyzer.py /var/log/meshtastic.log --json

    # Show only bad nodes
    python3 meshtastic_time_analyzer.py /var/log/meshtastic.log --bad-only

    # Show detailed chronological list of times each node reported
    python3 meshtastic_time_analyzer.py /var/log/meshtastic.log --detail

    # Analyze specific time range
    python3 meshtastic_time_analyzer.py /var/log/meshtastic.log --since "2026-01-10 00:00:00"
"""

import sys
import re
import argparse
import json
from datetime import datetime, timezone
from collections import defaultdict
from typing import Dict, List, Optional, Tuple


class LogAnalyzer:
    """Analyzes Meshtastic logs for time synchronization issues."""

    def __init__(self, time_threshold_seconds: int = 30, filter_epoch_zero: bool = True):
        """
        Initialize the log analyzer.

        Args:
            time_threshold_seconds: Maximum acceptable time difference in seconds
            filter_epoch_zero: If True, filter out entries with time=0 (1970-01-01)
        """
        self.time_threshold = time_threshold_seconds
        self.filter_epoch_zero = filter_epoch_zero
        self.node_data: Dict[str, List[Dict]] = defaultdict(list)
        self.filtered_count = 0  # Track how many epoch zero entries we filtered

        # Regex pattern for Router POSITION logs
        # Format: DEBUG | HH:MM:SS microsec [Router] POSITION node=hexid ... time=timestamp
        self.router_position_pattern = re.compile(
            r'\[Router\]\s+POSITION\s+node=([0-9a-fA-F]+).*?time=(\d+)'
        )

        # Optional: extract log timestamp if present
        # Format: 2026-01-11 12:34:56 | ...
        self.log_timestamp_pattern = re.compile(
            r'^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})'
        )

    def parse_line(self, line: str, line_number: int = 0) -> Optional[Dict]:
        """
        Parse a log line for Router POSITION data.

        Args:
            line: Log line to parse
            line_number: Line number in file (for reference)

        Returns:
            Dict with parsed data or None if no match
        """
        match = self.router_position_pattern.search(line)
        if not match:
            return None

        node_id = match.group(1)
        position_time = int(match.group(2))

        # Try to extract log timestamp
        log_time = None
        ts_match = self.log_timestamp_pattern.search(line)
        if ts_match:
            try:
                log_time = datetime.strptime(ts_match.group(1), '%Y-%m-%d %H:%M:%S')
                log_time = log_time.replace(tzinfo=timezone.utc)
            except:
                pass

        return {
            'node_id': f"0x{node_id}",
            'position_time': position_time,
            'log_time': log_time,
            'line_number': line_number
        }

    def add_entry(self, entry: Dict):
        """Add a parsed entry to the dataset."""
        node_id = entry['node_id']
        position_time = entry['position_time']
        log_time = entry['log_time']

        # Filter out epoch zero times (1970-01-01) if enabled
        # This includes times before Jan 2, 1970 (timestamp < 86400)
        if self.filter_epoch_zero and position_time < 86400:
            self.filtered_count += 1
            return

        # Calculate time difference
        if log_time:
            # Use log timestamp as reference
            reference_time = int(log_time.timestamp())
        else:
            # No log timestamp, can't calculate accurate diff
            # We'll mark this for later
            reference_time = None

        time_diff = abs(position_time - reference_time) if reference_time else None

        self.node_data[node_id].append({
            'position_time': position_time,
            'reference_time': reference_time,
            'time_diff': time_diff,
            'log_time': log_time,
            'line_number': entry['line_number']
        })

    def analyze(self, file_handle, since: Optional[datetime] = None):
        """
        Analyze log file.

        Args:
            file_handle: File handle to read from
            since: Optional datetime to filter entries (only analyze entries after this time)
        """
        for line_num, line in enumerate(file_handle, 1):
            entry = self.parse_line(line.strip(), line_num)
            if entry:
                # Filter by time if specified
                if since and entry['log_time']:
                    if entry['log_time'] < since:
                        continue

                self.add_entry(entry)

    def get_statistics(self) -> Dict:
        """
        Get statistics for all nodes.

        Returns:
            Dict with node statistics
        """
        stats = {}

        for node_id, entries in self.node_data.items():
            if not entries:
                continue

            # Sort entries chronologically by position_time
            sorted_entries = sorted(entries, key=lambda x: x['position_time'])

            # Filter entries with valid time_diff
            valid_entries = [e for e in sorted_entries if e['time_diff'] is not None]

            if not valid_entries:
                # No valid time comparisons
                stats[node_id] = {
                    'sample_count': len(entries),
                    'valid_samples': 0,
                    'has_time_diff': False,
                    'first_seen_line': entries[0]['line_number'],
                    'last_seen_line': entries[-1]['line_number'],
                    'entries': sorted_entries  # Include all entries
                }
                continue

            time_diffs = [e['time_diff'] for e in valid_entries]
            avg_diff = sum(time_diffs) / len(time_diffs)
            max_diff = max(time_diffs)
            min_diff = min(time_diffs)

            is_incorrect = max_diff > self.time_threshold

            stats[node_id] = {
                'sample_count': len(entries),
                'valid_samples': len(valid_entries),
                'has_time_diff': True,
                'avg_diff': avg_diff,
                'max_diff': max_diff,
                'min_diff': min_diff,
                'is_incorrect': is_incorrect,
                'first_seen': entries[0]['log_time'].isoformat() if entries[0]['log_time'] else None,
                'last_seen': entries[-1]['log_time'].isoformat() if entries[-1]['log_time'] else None,
                'first_seen_line': entries[0]['line_number'],
                'last_seen_line': entries[-1]['line_number'],
                'first_position_time': sorted_entries[0]['position_time'],
                'last_position_time': sorted_entries[-1]['position_time'],
                'entries': sorted_entries  # Include chronologically sorted entries
            }

        return stats


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


def print_statistics(stats: Dict, threshold: int, bad_only: bool = False, show_detail: bool = False, filtered_count: int = 0):
    """
    Print statistics in human-readable format.

    Args:
        stats: Statistics dictionary
        threshold: Time threshold for incorrect time
        bad_only: Only show nodes with bad time
        show_detail: Show detailed chronological list of reported times
        filtered_count: Number of epoch zero entries filtered
    """
    if not stats:
        print("No Router POSITION entries found in log.")
        if filtered_count > 0:
            print(f"(Filtered out {filtered_count} epoch zero entries)")
        return

    # Separate into good and bad nodes
    incorrect_nodes = []
    correct_nodes = []
    no_diff_nodes = []

    for node_id, node_stats in stats.items():
        if not node_stats['has_time_diff']:
            no_diff_nodes.append((node_id, node_stats))
        elif node_stats['is_incorrect']:
            incorrect_nodes.append((node_id, node_stats))
        else:
            correct_nodes.append((node_id, node_stats))

    # Sort by max time diff (worst first)
    incorrect_nodes.sort(key=lambda x: x[1]['max_diff'], reverse=True)
    correct_nodes.sort(key=lambda x: x[1]['avg_diff'], reverse=True)

    print("=" * 70)
    print("MESHTASTIC TIME ANALYSIS REPORT")
    print("=" * 70)
    print(f"Time threshold: {threshold}s")
    if filtered_count > 0:
        print(f"Filtered epoch zero entries: {filtered_count}")
    print(f"Total nodes found: {len(stats)}")
    print(f"  - Incorrect time: {len(incorrect_nodes)}")
    print(f"  - Correct time: {len(correct_nodes)}")
    print(f"  - No timestamp data: {len(no_diff_nodes)}")
    print("=" * 70)

    if incorrect_nodes:
        print(f"\n❌ NODES WITH INCORRECT TIME ({len(incorrect_nodes)}):\n")
        for node_id, node_stats in incorrect_nodes:
            print(f"Node: {node_id}")
            print(f"  Samples: {node_stats['sample_count']} ({node_stats['valid_samples']} with time diff)")
            print(f"  Average diff: {format_time_diff(int(node_stats['avg_diff']))}")
            print(f"  Max diff: {format_time_diff(int(node_stats['max_diff']))}")
            print(f"  Min diff: {format_time_diff(int(node_stats['min_diff']))}")

            # Show chronological time range
            print(f"  First reported time: {format_timestamp(node_stats['first_position_time'])}")
            print(f"  Last reported time: {format_timestamp(node_stats['last_position_time'])}")

            if node_stats['first_seen']:
                print(f"  Log time range: {node_stats['first_seen']} to {node_stats['last_seen']}")

            # Show detailed chronological list if requested
            if show_detail and 'entries' in node_stats:
                entries = node_stats['entries']
                print(f"\n  Chronological time reports:")

                # Show first 5 and last 5 if more than 10 entries
                if len(entries) > 10:
                    print(f"  (Showing first 5 and last 5 of {len(entries)} total)")
                    display_entries = entries[:5] + entries[-5:]
                    show_ellipsis = True
                else:
                    display_entries = entries
                    show_ellipsis = False

                for i, entry in enumerate(display_entries):
                    if show_ellipsis and i == 5:
                        print(f"    ...")

                    reported_time = format_timestamp(entry['position_time'])
                    if entry['time_diff'] is not None:
                        diff_str = f"diff: {format_time_diff(int(entry['time_diff']))}"
                    else:
                        diff_str = "diff: N/A"

                    if entry['log_time']:
                        log_time_str = entry['log_time'].strftime('%Y-%m-%d %H:%M:%S')
                        print(f"    [{log_time_str}] Reported: {reported_time} ({diff_str})")
                    else:
                        print(f"    [line {entry['line_number']}] Reported: {reported_time} ({diff_str})")
                print()
            else:
                print()

    if not bad_only and correct_nodes:
        print(f"✓ NODES WITH CORRECT TIME ({len(correct_nodes)}):\n")
        for node_id, node_stats in correct_nodes:
            print(f"Node: {node_id}")
            print(f"  Samples: {node_stats['sample_count']}, "
                  f"Avg diff: {format_time_diff(int(node_stats['avg_diff']))}, "
                  f"Max diff: {format_time_diff(int(node_stats['max_diff']))}")

            # Show chronological time range
            print(f"  First reported time: {format_timestamp(node_stats['first_position_time'])}")
            print(f"  Last reported time: {format_timestamp(node_stats['last_position_time'])}")

            if node_stats['first_seen']:
                print(f"  Log time range: {node_stats['first_seen']} to {node_stats['last_seen']}")

            # Show detailed chronological list if requested
            if show_detail and 'entries' in node_stats:
                entries = node_stats['entries']
                print(f"\n  Chronological time reports:")

                # Show first 5 and last 5 if more than 10 entries
                if len(entries) > 10:
                    print(f"  (Showing first 5 and last 5 of {len(entries)} total)")
                    display_entries = entries[:5] + entries[-5:]
                    show_ellipsis = True
                else:
                    display_entries = entries
                    show_ellipsis = False

                for i, entry in enumerate(display_entries):
                    if show_ellipsis and i == 5:
                        print(f"    ...")

                    reported_time = format_timestamp(entry['position_time'])
                    if entry['time_diff'] is not None:
                        diff_str = f"diff: {format_time_diff(int(entry['time_diff']))}"
                    else:
                        diff_str = "diff: N/A"

                    if entry['log_time']:
                        log_time_str = entry['log_time'].strftime('%Y-%m-%d %H:%M:%S')
                        print(f"    [{log_time_str}] Reported: {reported_time} ({diff_str})")
                    else:
                        print(f"    [line {entry['line_number']}] Reported: {reported_time} ({diff_str})")
            print()

    if not bad_only and no_diff_nodes:
        print(f"⚠ NODES WITHOUT TIMESTAMP DATA ({len(no_diff_nodes)}):\n")
        print("(Log entries don't have timestamps - can't calculate time difference)\n")
        for node_id, node_stats in no_diff_nodes:
            print(f"Node: {node_id} - {node_stats['sample_count']} samples")

            # Show chronological time range
            if 'entries' in node_stats:
                entries = node_stats['entries']
                print(f"  First reported time: {format_timestamp(entries[0]['position_time'])}")
                print(f"  Last reported time: {format_timestamp(entries[-1]['position_time'])}")

                # Show detailed list if requested
                if show_detail:
                    print(f"\n  Chronological time reports:")
                    if len(entries) > 10:
                        print(f"  (Showing first 5 and last 5 of {len(entries)} total)")
                        display_entries = entries[:5] + entries[-5:]
                        show_ellipsis = True
                    else:
                        display_entries = entries
                        show_ellipsis = False

                    for i, entry in enumerate(display_entries):
                        if show_ellipsis and i == 5:
                            print(f"    ...")
                        reported_time = format_timestamp(entry['position_time'])
                        print(f"    [line {entry['line_number']}] Reported: {reported_time}")
            print()

    print("\n" + "=" * 70)


def output_json(stats: Dict):
    """Output statistics as JSON."""
    # Convert to JSON-serializable format
    output = {
        'nodes': {}
    }

    for node_id, node_stats in stats.items():
        output['nodes'][node_id] = {
            'sample_count': node_stats['sample_count'],
            'valid_samples': node_stats.get('valid_samples', 0),
            'has_time_diff': node_stats['has_time_diff']
        }

        if node_stats['has_time_diff']:
            output['nodes'][node_id].update({
                'avg_diff_seconds': node_stats['avg_diff'],
                'max_diff_seconds': node_stats['max_diff'],
                'min_diff_seconds': node_stats['min_diff'],
                'is_incorrect': node_stats['is_incorrect'],
                'first_seen': node_stats['first_seen'],
                'last_seen': node_stats['last_seen'],
                'first_position_time': node_stats['first_position_time'],
                'last_position_time': node_stats['last_position_time']
            })

        output['nodes'][node_id].update({
            'first_seen_line': node_stats['first_seen_line'],
            'last_seen_line': node_stats['last_seen_line']
        })

        # Add chronological entries
        if 'entries' in node_stats:
            output['nodes'][node_id]['chronological_entries'] = []
            for entry in node_stats['entries']:
                entry_data = {
                    'position_time': entry['position_time'],
                    'position_time_formatted': format_timestamp(entry['position_time']),
                    'line_number': entry['line_number']
                }
                if entry['time_diff'] is not None:
                    entry_data['time_diff_seconds'] = entry['time_diff']
                if entry['log_time']:
                    entry_data['log_time'] = entry['log_time'].isoformat()
                if entry['reference_time']:
                    entry_data['reference_time'] = entry['reference_time']

                output['nodes'][node_id]['chronological_entries'].append(entry_data)

    print(json.dumps(output, indent=2))


def main():
    parser = argparse.ArgumentParser(
        description='Analyze Meshtastic log files for time synchronization issues'
    )

    parser.add_argument('logfile',
                       help='Log file to analyze (use "-" for stdin)')
    parser.add_argument('--threshold', type=int, default=30,
                       help='Time difference threshold in seconds (default: 30)')
    parser.add_argument('--json', action='store_true',
                       help='Output as JSON instead of human-readable format')
    parser.add_argument('--bad-only', action='store_true',
                       help='Only show nodes with incorrect time')
    parser.add_argument('--since', type=str,
                       help='Only analyze entries after this time (format: "YYYY-MM-DD HH:MM:SS")')
    parser.add_argument('--stats', action='store_true',
                       help='Show processing statistics')
    parser.add_argument('--detail', action='store_true',
                       help='Show detailed chronological list of reported times for each node')
    parser.add_argument('--include-epoch-zero', action='store_true',
                       help='Include entries with time=0 (1970-01-01 00:00:00 UTC) - by default these are filtered out')

    args = parser.parse_args()

    # Parse --since if provided
    since_dt = None
    if args.since:
        try:
            since_dt = datetime.strptime(args.since, '%Y-%m-%d %H:%M:%S')
            since_dt = since_dt.replace(tzinfo=timezone.utc)
        except ValueError:
            print(f"Error: Invalid --since format. Use: 'YYYY-MM-DD HH:MM:SS'")
            sys.exit(1)

    # Initialize analyzer
    analyzer = LogAnalyzer(
        time_threshold_seconds=args.threshold,
        filter_epoch_zero=not args.include_epoch_zero
    )

    # Read from file or stdin
    try:
        if args.logfile == '-':
            if args.stats:
                print("Reading from stdin...", file=sys.stderr)
            analyzer.analyze(sys.stdin, since=since_dt)
        else:
            if args.stats:
                print(f"Analyzing {args.logfile}...", file=sys.stderr)
            with open(args.logfile, 'r') as f:
                analyzer.analyze(f, since=since_dt)
    except FileNotFoundError:
        print(f"Error: File not found: {args.logfile}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nAnalysis interrupted by user")
        sys.exit(1)

    # Get statistics
    stats = analyzer.get_statistics()

    if args.stats:
        total_entries = sum(s['sample_count'] for s in stats.values())
        print(f"Processed {total_entries} Router POSITION entries", file=sys.stderr)
        if analyzer.filtered_count > 0:
            print(f"Filtered out {analyzer.filtered_count} epoch zero (1970-01-01) entries", file=sys.stderr)
        print(f"Found {len(stats)} unique nodes", file=sys.stderr)
        print("", file=sys.stderr)

    # Output results
    if args.json:
        output_json(stats)
    else:
        print_statistics(stats, args.threshold, args.bad_only, args.detail, analyzer.filtered_count)


if __name__ == '__main__':
    main()
