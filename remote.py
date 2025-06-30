"""
Remote server access via SSH for Fend Sentry

Provides secure SSH connections to read Django log files remotely
without downloading them locally.
"""

import paramiko
import socket
import time
from pathlib import Path
from typing import List, Optional, Dict, Any
from io import StringIO

class ConnectionError(Exception):
    """SSH connection related errors"""
    pass

class RemoteConnection:
    """Manages SSH connections to remote servers"""
    
    def __init__(self, server_config: Dict[str, Any]):
        """Initialize remote connection
        
        Args:
            server_config: Server configuration dictionary with:
                - host: Hostname or IP address
                - port: SSH port (default 22)
                - username: SSH username
                - private_key_path: Path to SSH private key (optional)
                - password: SSH password (optional)
        """
        self.host = server_config['host']
        self.port = server_config.get('port', 22)
        self.username = server_config['username']
        self.private_key_path = server_config.get('private_key_path')
        self.password = server_config.get('password')
        
        self.client = None
        self.sftp = None
        self.connected = False
    
    def connect(self, timeout: int = 10):
        """Establish SSH connection
        
        Args:
            timeout: Connection timeout in seconds
            
        Raises:
            ConnectionError: If connection fails
        """
        try:
            self.client = paramiko.SSHClient()
            
            # Configure host key policy (accept unknown hosts)
            # In production, you might want to use a more restrictive policy
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Prepare connection parameters
            connect_kwargs = {
                'hostname': self.host,
                'port': self.port,
                'username': self.username,
                'timeout': timeout,
                'look_for_keys': False,  # Don't automatically look for keys
                'allow_agent': False     # Don't use SSH agent
            }
            
            # Handle authentication
            if self.private_key_path:
                # SSH key authentication
                key_path = Path(self.private_key_path).expanduser()
                if not key_path.exists():
                    raise ConnectionError(f"SSH private key not found: {self.private_key_path}")
                
                try:
                    # Try different key types
                    private_key = None
                    for key_class in [paramiko.RSAKey, paramiko.Ed25519Key, paramiko.ECDSAKey, paramiko.DSSKey]:
                        try:
                            private_key = key_class.from_private_key_file(str(key_path))
                            break
                        except paramiko.ssh_exception.SSHException:
                            continue
                    
                    if private_key is None:
                        raise ConnectionError(f"Unable to load SSH private key: {self.private_key_path}")
                    
                    connect_kwargs['pkey'] = private_key
                    
                except Exception as e:
                    raise ConnectionError(f"Failed to load SSH private key: {e}")
            
            elif self.password:
                # Password authentication
                connect_kwargs['password'] = self.password
            
            else:
                raise ConnectionError("No authentication method specified (key or password)")
            
            # Establish connection
            self.client.connect(**connect_kwargs)
            
            # Initialize SFTP for file operations
            self.sftp = self.client.open_sftp()
            
            self.connected = True
            
        except socket.timeout:
            raise ConnectionError(f"Connection timed out connecting to {self.host}:{self.port}")
        except socket.gaierror:
            raise ConnectionError(f"Could not resolve hostname: {self.host}")
        except paramiko.AuthenticationException:
            raise ConnectionError("SSH authentication failed")
        except paramiko.SSHException as e:
            raise ConnectionError(f"SSH connection error: {e}")
        except Exception as e:
            raise ConnectionError(f"Failed to connect: {e}")
    
    def disconnect(self):
        """Close SSH connection"""
        try:
            if self.sftp:
                self.sftp.close()
                self.sftp = None
            
            if self.client:
                self.client.close()
                self.client = None
            
            self.connected = False
            
        except Exception:
            # Ignore errors during cleanup
            pass
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()
    
    def read_log_file(self, file_path: str, lines: int = 1000) -> List[str]:
        """Read recent lines from a log file
        
        Args:
            file_path: Path to log file on remote server
            lines: Number of recent lines to read (default 1000)
            
        Returns:
            List of log lines
            
        Raises:
            ConnectionError: If reading fails
        """
        if not self.connected:
            raise ConnectionError("Not connected to server")
        
        try:
            # Use tail command to get recent lines efficiently
            command = f"tail -n {lines} '{file_path}' 2>/dev/null || echo 'FILE_NOT_FOUND'"
            
            stdin, stdout, stderr = self.client.exec_command(command)
            
            # Read output
            output = stdout.read().decode('utf-8', errors='replace')
            error = stderr.read().decode('utf-8', errors='replace')
            
            # Check for errors
            if output.strip() == 'FILE_NOT_FOUND':
                raise ConnectionError(f"Log file not found: {file_path}")
            
            if error and "No such file or directory" in error:
                raise ConnectionError(f"Log file not found: {file_path}")
            
            # Split into lines and filter empty lines
            log_lines = [line for line in output.split('\n') if line.strip()]
            
            return log_lines
            
        except paramiko.SSHException as e:
            raise ConnectionError(f"SSH command execution failed: {e}")
        except Exception as e:
            raise ConnectionError(f"Failed to read log file: {e}")
    
    def check_file_exists(self, file_path: str) -> bool:
        """Check if a file exists on the remote server
        
        Args:
            file_path: Path to check
            
        Returns:
            True if file exists, False otherwise
        """
        if not self.connected:
            return False
        
        try:
            command = f"test -f '{file_path}' && echo 'EXISTS' || echo 'NOT_EXISTS'"
            stdin, stdout, stderr = self.client.exec_command(command)
            output = stdout.read().decode('utf-8').strip()
            return output == 'EXISTS'
            
        except Exception:
            return False
    
    def get_file_info(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Get information about a file
        
        Args:
            file_path: Path to file
            
        Returns:
            Dictionary with file info or None if file doesn't exist
        """
        if not self.connected:
            return None
        
        try:
            # Get file stats using ls -la
            command = f"ls -la '{file_path}' 2>/dev/null"
            stdin, stdout, stderr = self.client.exec_command(command)
            output = stdout.read().decode('utf-8').strip()
            
            if not output:
                return None
            
            # Parse ls output (basic parsing)
            parts = output.split()
            if len(parts) >= 5:
                return {
                    'size': parts[4],
                    'modified': ' '.join(parts[5:8]) if len(parts) >= 8 else 'unknown',
                    'permissions': parts[0]
                }
            
            return None
            
        except Exception:
            return None
    
    def execute_command(self, command: str, timeout: int = 30) -> Dict[str, str]:
        """Execute a command on the remote server
        
        Args:
            command: Command to execute
            timeout: Command timeout in seconds
            
        Returns:
            Dictionary with 'stdout', 'stderr', and 'exit_code'
            
        Raises:
            ConnectionError: If command execution fails
        """
        if not self.connected:
            raise ConnectionError("Not connected to server")
        
        try:
            stdin, stdout, stderr = self.client.exec_command(command, timeout=timeout)
            
            # Read output
            stdout_data = stdout.read().decode('utf-8', errors='replace')
            stderr_data = stderr.read().decode('utf-8', errors='replace')
            exit_code = stdout.channel.recv_exit_status()
            
            return {
                'stdout': stdout_data,
                'stderr': stderr_data,
                'exit_code': exit_code
            }
            
        except socket.timeout:
            raise ConnectionError(f"Command timed out after {timeout} seconds")
        except Exception as e:
            raise ConnectionError(f"Command execution failed: {e}")
    
    def test_connection(self) -> bool:
        """Test if connection is working
        
        Returns:
            True if connection is working, False otherwise
        """
        try:
            if not self.connected:
                return False
            
            # Simple test command
            result = self.execute_command('echo "test"', timeout=5)
            return result['exit_code'] == 0 and 'test' in result['stdout']
            
        except Exception:
            return False