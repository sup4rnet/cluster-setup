"""IP allocation logic for tenant VMs."""

import re
from pathlib import Path

from .config import (
    HOST_VARS_DIR,
    IP_NETWORK,
    IP_SUBNET_MASK,
    RESERVED_IPS,
    VM_IP_END,
    VM_IP_START,
)
from .models import IPAllocation
from .yaml_editor import load_yaml


def scan_used_ips() -> set[int]:
    """Scan all host_vars files and return set of used IP last octets.

    Returns:
        Set of used IP last octets (e.g., {13, 14, 15, 16, 19, 20})
    """
    used_ips: set[int] = set()

    # Pattern to match restvm-*.yaml files
    for yaml_file in HOST_VARS_DIR.glob("restvm-*.yaml"):
        try:
            data = load_yaml(yaml_file)
            if data and "dataplane_ipv4" in data:
                for ip_entry in data["dataplane_ipv4"]:
                    # Extract last octet from IP like "10.10.0.13/24"
                    match = re.search(r"\.(\d+)/", str(ip_entry))
                    if match:
                        used_ips.add(int(match.group(1)))
        except Exception:
            # Skip files that can't be parsed
            continue

    return used_ips


def get_all_used_ips() -> set[int]:
    """Get all used and reserved IPs.

    Returns:
        Set of all unavailable IP last octets
    """
    return RESERVED_IPS | scan_used_ips()


def allocate_ip_pair() -> IPAllocation | None:
    """Allocate a consecutive pair of IPs for a new tenant.

    Returns:
        IPAllocation with two consecutive IPs, or None if no space available
    """
    used = get_all_used_ips()

    # Find first available consecutive pair
    for start in range(VM_IP_START, VM_IP_END, 2):
        if start not in used and (start + 1) not in used:
            ip1 = f"{IP_NETWORK}.{start}/{IP_SUBNET_MASK}"
            ip2 = f"{IP_NETWORK}.{start + 1}/{IP_SUBNET_MASK}"
            return IPAllocation(ip1=ip1, ip2=ip2)

    return None


def get_ip_status() -> dict:
    """Get detailed IP allocation status.

    Returns:
        Dictionary with allocation statistics and details
    """
    used = scan_used_ips()
    reserved = RESERVED_IPS

    available = []
    for ip in range(VM_IP_START, VM_IP_END + 1):
        if ip not in used and ip not in reserved:
            available.append(ip)

    # Find available pairs
    available_pairs = []
    for start in range(VM_IP_START, VM_IP_END, 2):
        if start not in used and start not in reserved:
            if (start + 1) not in used and (start + 1) not in reserved:
                available_pairs.append((start, start + 1))

    return {
        "total_range": (VM_IP_START, VM_IP_END),
        "reserved": sorted(reserved),
        "used": sorted(used),
        "available_count": len(available),
        "available_pairs_count": len(available_pairs),
        "next_pair": available_pairs[0] if available_pairs else None,
    }


def get_ip_to_vm_mapping() -> dict[str, str]:
    """Map IPs to VM names.

    Returns:
        Dictionary mapping IP (without mask) to VM name
    """
    ip_to_vm: dict[str, str] = {}

    for yaml_file in HOST_VARS_DIR.glob("restvm-*.yaml"):
        try:
            data = load_yaml(yaml_file)
            vm_name = yaml_file.stem
            if data and "dataplane_ipv4" in data:
                for ip_entry in data["dataplane_ipv4"]:
                    ip_bare = str(ip_entry).split("/")[0]
                    ip_to_vm[ip_bare] = vm_name
        except Exception:
            continue

    return ip_to_vm
