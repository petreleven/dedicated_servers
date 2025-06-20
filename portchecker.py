import subprocess
import re
from typing import List


def _run_cmd(cmd: str):
    """Run a shell command and return (returncode, stdout, stderr)."""
    process = subprocess.Popen(
        args=cmd, shell=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True
    )
    stdout, stderr = process.communicate()
    return process.returncode, stdout, stderr


def _get_used_ports(stdout: str) -> List[str]:
    """Extract used port numbers from netstat output."""
    used_ports = []
    for line in stdout.splitlines():
        match = re.search(r":(\d+)\s", line)
        if match:
            used_ports.append(match.group(1))
    return used_ports


def get_available_ports(start: int = 2300, end: int = 8000, n=5) -> List[int]:
    """Return a list of available ports in the given range."""
    available_ports = []
    returncode, stdout, stderr = _run_cmd("ss -tuln")
    if returncode != 0:
        return available_ports

    used_ports = _get_used_ports(stdout)
    for port in range(start, end):
        if str(port) not in used_ports:
            available_ports.append(port)

    return available_ports[:n]
