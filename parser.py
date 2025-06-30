"""
Django log parser for Fend Sentry

Intelligently parses Django application logs to extract structured information
including errors, warnings, and system events.
"""

import re
import hashlib
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict

@dataclass
class LogEntry:
    """Structured log entry"""
    timestamp: Optional[datetime] = None
    level: str = ""
    logger: str = ""
    message: str = ""
    traceback: List[str] = field(default_factory=list)
    raw_line: str = ""
    line_number: int = 0
    
    # Extracted metadata
    request_id: Optional[str] = None
    user_id: Optional[str] = None
    ip_address: Optional[str] = None
    url_path: Optional[str] = None
    status_code: Optional[int] = None
    
    def __post_init__(self):
        """Extract additional metadata from message"""
        self._extract_metadata()
    
    def _extract_metadata(self):
        """Extract structured data from log message"""
        # Extract IP addresses
        ip_pattern = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
        ip_match = re.search(ip_pattern, self.message)
        if ip_match:
            self.ip_address = ip_match.group()
        
        # Extract URL paths
        url_pattern = r'"[A-Z]+ ([^"]+) HTTP'
        url_match = re.search(url_pattern, self.message)
        if url_match:
            self.url_path = url_match.group(1)
        
        # Extract HTTP status codes
        status_pattern = r'" (\d{3}) '
        status_match = re.search(status_pattern, self.message)
        if status_match:
            self.status_code = int(status_match.group(1))
        
        # Extract Django request IDs (if present)
        request_id_pattern = r'rid=([a-f0-9-]+)'
        request_match = re.search(request_id_pattern, self.message)
        if request_match:
            self.request_id = request_match.group(1)
    
    @property
    def error_signature(self) -> str:
        """Generate unique signature for similar errors"""
        # Use exception type and location for grouping
        signature_parts = [self.level, self.logger]
        
        # Extract exception type from message
        exception_match = re.search(r'(\w+Error|Exception):', self.message)
        if exception_match:
            signature_parts.append(exception_match.group(1))
        
        # Use first line of traceback if available
        if self.traceback:
            # Find the actual error location (not Django internal)
            for line in self.traceback:
                if '/site-packages/' not in line and 'File "/' in line:
                    signature_parts.append(line.strip())
                    break
        
        signature_str = '|'.join(signature_parts)
        return hashlib.md5(signature_str.encode()).hexdigest()[:8]
    
    @property
    def is_error(self) -> bool:
        """Check if this is an error-level log entry"""
        return self.level.upper() in ['ERROR', 'CRITICAL', 'FATAL']
    
    @property
    def is_warning(self) -> bool:
        """Check if this is a warning-level log entry"""
        return self.level.upper() == 'WARNING'

@dataclass
class ErrorGroup:
    """Group of similar errors"""
    signature: str
    count: int = 0
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    example_entry: Optional[LogEntry] = None
    entries: List[LogEntry] = field(default_factory=list)
    
    def add_entry(self, entry: LogEntry):
        """Add a log entry to this group"""
        self.entries.append(entry)
        self.count += 1
        
        if not self.first_seen or (entry.timestamp and entry.timestamp < self.first_seen):
            self.first_seen = entry.timestamp
        
        if not self.last_seen or (entry.timestamp and entry.timestamp > self.last_seen):
            self.last_seen = entry.timestamp
        
        # Keep the most recent as example
        if not self.example_entry or (entry.timestamp and 
            (not self.example_entry.timestamp or entry.timestamp > self.example_entry.timestamp)):
            self.example_entry = entry

class LogParser:
    """Django log parser"""
    
    # Common Django log patterns
    DJANGO_LOG_PATTERNS = [
        # Standard Django format: [timestamp] LEVEL logger: message
        re.compile(r'^\[([^\]]+)\]\s+(\w+)\s+([^:]+):\s*(.+)$'),
        
        # Python logging format: timestamp - logger - LEVEL - message  
        re.compile(r'^([0-9-]+\s+[0-9:,]+)\s+-\s+([^-]+)\s+-\s+(\w+)\s+-\s*(.+)$'),
        
        # Simple format: timestamp LEVEL: message
        re.compile(r'^([0-9-]+\s+[0-9:,]+)\s+(\w+):\s*(.+)$'),
        
        # Gunicorn/uWSGI format
        re.compile(r'^\[([^\]]+)\]\s+\[(\w+)\]\s*(.+)$'),
    ]
    
    # Timestamp patterns
    TIMESTAMP_PATTERNS = [
        '%Y-%m-%d %H:%M:%S,%f',  # 2024-01-01 12:00:00,123
        '%Y-%m-%d %H:%M:%S.%f',  # 2024-01-01 12:00:00.123456
        '%Y-%m-%d %H:%M:%S',     # 2024-01-01 12:00:00
        '%d/%b/%Y %H:%M:%S',     # 01/Jan/2024 12:00:00
        '%d/%b/%Y:%H:%M:%S %z',  # 01/Jan/2024:12:00:00 +0000
    ]
    
    def __init__(self):
        self.entries: List[LogEntry] = []
        self.error_groups: Dict[str, ErrorGroup] = {}
    
    def parse_logs(self, log_lines: List[str]) -> Dict[str, Any]:
        """Parse log lines into structured format
        
        Args:
            log_lines: List of raw log lines
            
        Returns:
            Dictionary with parsed results
        """
        self.entries = []
        self.error_groups = {}
        
        current_entry = None
        in_traceback = False
        
        for line_num, line in enumerate(log_lines, 1):
            line = line.rstrip()
            
            if not line:
                continue
            
            # Check if this is a new log entry
            parsed = self._parse_log_line(line)
            
            if parsed:
                # Save previous entry if exists
                if current_entry:
                    self._finalize_entry(current_entry)
                
                # Start new entry
                timestamp, level, logger, message = parsed
                current_entry = LogEntry(
                    timestamp=timestamp,
                    level=level,
                    logger=logger,
                    message=message,
                    raw_line=line,
                    line_number=line_num
                )
                in_traceback = False
                
            elif current_entry and (in_traceback or self._is_traceback_line(line)):
                # This is a continuation line (traceback)
                current_entry.traceback.append(line)
                in_traceback = True
                
            elif current_entry:
                # Multi-line message continuation
                current_entry.message += ' ' + line.strip()
        
        # Don't forget the last entry
        if current_entry:
            self._finalize_entry(current_entry)
        
        # Group similar errors
        self._group_errors()
        
        return self._generate_summary()
    
    def _parse_log_line(self, line: str) -> Optional[Tuple[Optional[datetime], str, str, str]]:
        """Parse a single log line
        
        Returns:
            Tuple of (timestamp, level, logger, message) or None
        """
        for pattern in self.DJANGO_LOG_PATTERNS:
            match = pattern.match(line)
            if match:
                groups = match.groups()
                
                if len(groups) == 4:
                    # Format: [timestamp] LEVEL logger: message
                    timestamp_str, level, logger, message = groups
                    timestamp = self._parse_timestamp(timestamp_str)
                    return timestamp, level.upper(), logger.strip(), message
                
                elif len(groups) == 3:
                    if pattern == self.DJANGO_LOG_PATTERNS[3]:  # Gunicorn format
                        timestamp_str, level, message = groups
                        timestamp = self._parse_timestamp(timestamp_str)
                        return timestamp, level.upper(), 'gunicorn', message
                    else:  # Simple format
                        timestamp_str, level, message = groups
                        timestamp = self._parse_timestamp(timestamp_str)
                        return timestamp, level.upper(), 'django', message
        
        return None
    
    def _parse_timestamp(self, timestamp_str: str) -> Optional[datetime]:
        """Parse timestamp string into datetime object"""
        timestamp_str = timestamp_str.strip()
        
        for pattern in self.TIMESTAMP_PATTERNS:
            try:
                return datetime.strptime(timestamp_str, pattern)
            except ValueError:
                continue
        
        # Try to extract just date/time part if there are extra characters
        timestamp_match = re.search(r'([0-9-]+\s+[0-9:,\.]+)', timestamp_str)
        if timestamp_match:
            clean_timestamp = timestamp_match.group(1)
            for pattern in self.TIMESTAMP_PATTERNS:
                try:
                    return datetime.strptime(clean_timestamp, pattern)
                except ValueError:
                    continue
        
        return None
    
    def _is_traceback_line(self, line: str) -> bool:
        """Check if line is part of a traceback"""
        traceback_indicators = [
            'Traceback (most recent call last):',
            '  File "',
            '    ',
            'During handling of the above exception',
            'The above exception was the direct cause',
        ]
        
        return any(indicator in line for indicator in traceback_indicators)
    
    def _finalize_entry(self, entry: LogEntry):
        """Finalize and store a log entry"""
        self.entries.append(entry)
    
    def _group_errors(self):
        """Group similar errors together"""
        for entry in self.entries:
            if entry.is_error:
                signature = entry.error_signature
                
                if signature not in self.error_groups:
                    self.error_groups[signature] = ErrorGroup(signature=signature)
                
                self.error_groups[signature].add_entry(entry)
    
    def _generate_summary(self) -> Dict[str, Any]:
        """Generate summary of parsed logs"""
        now = datetime.now()
        twenty_four_hours_ago = datetime.fromtimestamp(now.timestamp() - 24*3600)
        one_hour_ago = datetime.fromtimestamp(now.timestamp() - 3600)
        
        # Count entries by level
        level_counts = defaultdict(int)
        recent_errors = []
        recent_warnings = []
        
        for entry in self.entries:
            level_counts[entry.level] += 1
            
            # Collect recent errors and warnings
            if entry.timestamp and entry.timestamp > one_hour_ago:
                if entry.is_error:
                    recent_errors.append(entry)
                elif entry.is_warning:
                    recent_warnings.append(entry)
        
        # Sort error groups by count
        sorted_error_groups = sorted(
            self.error_groups.values(),
            key=lambda g: g.count,
            reverse=True
        )
        
        return {
            'total_entries': len(self.entries),
            'level_counts': dict(level_counts),
            'error_groups': sorted_error_groups,
            'recent_errors': recent_errors[-10:],  # Last 10 errors
            'recent_warnings': recent_warnings[-10:],  # Last 10 warnings
            'entries': self.entries,
            'parsing_timestamp': now
        }
    
    def get_error_trends(self, hours: int = 24) -> Dict[str, Any]:
        """Analyze error trends over time"""
        now = datetime.now()
        cutoff_time = datetime.fromtimestamp(now.timestamp() - hours*3600)
        
        # Count errors by hour
        hourly_errors = defaultdict(int)
        hourly_warnings = defaultdict(int)
        
        for entry in self.entries:
            if not entry.timestamp or entry.timestamp < cutoff_time:
                continue
            
            hour_key = entry.timestamp.strftime('%Y-%m-%d %H:00')
            
            if entry.is_error:
                hourly_errors[hour_key] += 1
            elif entry.is_warning:
                hourly_warnings[hour_key] += 1
        
        return {
            'hourly_errors': dict(hourly_errors),
            'hourly_warnings': dict(hourly_warnings),
            'total_errors_period': sum(hourly_errors.values()),
            'total_warnings_period': sum(hourly_warnings.values())
        }