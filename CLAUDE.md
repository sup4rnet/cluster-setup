# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an Ansible automation repository for managing the SUPERNET P4 programmable network cluster at Politecnico di Torino. It provisions tenant VMs with Intel P4 Studio (SDE 9.13.2) and manages access to two Intel Tofino programmable switches (`rest-bfsw01`, `rest-bfsw02`).

## Architecture

### Infrastructure Components

**Physical Layer:**
- `restsrv01.polito.it`: Debian 12 server hosting tenant VMs (KVM/libvirt/QEMU)
- `rest-bfsw01.polito.it`, `rest-bfsw02.polito.it`: Intel Tofino P4 switches with control-plane CPUs (Ubuntu 20.04)

**Network Architecture:**
- Dataplane network: `10.10.0.0/24` (bridged to VMs, connects to Tofino switches)
- Reserved IPs: `.2-.5` (switches), `.10, .101` (server)
- VM IP allocation: `.11-.100` (allocated in consecutive pairs per VM)
- NAT interface: Provides internet access to VMs (not routed through switches)

**Access Model:**
- VMs are accessed via SSH proxy jump through `restsrv01` (bastion host)
- VM hostnames only resolve locally at `restsrv01` (libvirt-nss plugin)
- External access requires PoliTO VPN

### Ansible Inventory Structure

**Host Groups:**
- `p4switches`: Control-plane CPUs on both Tofino switches
- `rest_bfsw02`: Separate group for targeting only the second switch
- `servers`: Physical server `restsrv01`
- `vms`: All tenant virtual machines (accessed via SSH proxy)

**Admin-Specific Inventories:**
Each admin has their own inventory file (`inventory-{admin}.yaml`) with their SSH username and ProxyCommand configuration, synchronized with the main `inventory.yaml`.

### Configuration Files Hierarchy

**Global Configuration:**
- `group_vars/all.yaml`: SDE paths, global variables, `restart_users` list (users authorized on switches and webapp)
- `group_vars/p4switches.yaml`, `group_vars/servers.yaml`, `group_vars/vms.yaml`: Group-specific variables

**Per-Host Configuration:**
- `host_vars/restsrv01.yaml`: List of all VMs (`vms` variable), server-specific config
- `host_vars/restvm-{user}-{nn}.yaml`: Per-VM config including `dataplane_ipv4` (array of IPs with `/24` CIDR) and `host_users` (array of usernames)
- `host_vars/rest-bfsw01.yaml`, `host_vars/rest-bfsw02.yaml`: Switch-specific config

**Inventory Files:**
- `inventory.yaml`: Main inventory with all hosts
- `inventory-{admin}.yaml`: Admin-specific inventories with custom SSH configurations

### Tenant Lifecycle

**Adding a Tenant (Full Flow):**
1. Add username to `restart_users` in `group_vars/all.yaml`
2. Add VM name to `vms` list in `host_vars/restsrv01.yaml`
3. Create `host_vars/restvm-{user}-{nn}.yaml` with `dataplane_ipv4` and `host_users`
4. Add VM to `inventory.yaml` under `vms.hosts`
5. Sync admin-specific inventory if needed
6. Run `playbooks/adduser.yaml` which:
   - Creates KVM VM with bridged networking (role: `kvm_provision`)
   - Bootstraps user accounts on P4 switches (role: `bootstrap`)
   - Configures networking and P4 SDE on VM (roles: `bootstrap`, `netplan`)
   - Adds user to server and webapp database

**Removing a Tenant:**
1. Run `playbooks/removeuser.yaml` to delete VMs, remove user from switches/webapp/server
2. Manually update config files (or use `p4tenant-cli`)

## Common Commands

### Using the p4tenant CLI Tool (Recommended)

The `p4tenant-cli` wrapper script automates tenant management:

```bash
# List all tenants and their configuration status
./p4tenant-cli list

# Add a new user with interactive prompts
./p4tenant-cli add user

# Add a VM to an existing user
./p4tenant-cli add vm

# Remove a tenant (interactive)
./p4tenant-cli remove

# Show IP allocation status
./p4tenant-cli ip-status

# Apply/provision an existing tenant
./p4tenant-cli apply <username>
```

The CLI automatically handles IP allocation, YAML editing, inventory synchronization, and can optionally run ansible-playbook.

### Manual Ansible Playbook Execution

**Full tenant onboarding:**
```bash
ansible-playbook playbooks/adduser.yaml -i inventory.yaml -K
```

**Run specific stages with tags:**
```bash
# Only create VMs
ansible-playbook playbooks/adduser.yaml -i inventory.yaml --tags kvmconf

# Only configure P4 switches
ansible-playbook playbooks/adduser.yaml -i inventory.yaml --tags p4conf -K

# Only bootstrap VMs
ansible-playbook playbooks/adduser.yaml -i inventory.yaml --tags vmboot -K

# Only add users to server and webapp
ansible-playbook playbooks/adduser.yaml -i inventory.yaml --tags srvuseradd -K
```

**Individual playbooks:**
```bash
# Create VMs with bridged networking
ansible-playbook playbooks/kvm-bridged-net.yaml -i inventory.yaml

# Bootstrap Tofino switches
ansible-playbook playbooks/bootstrap-tofino.yaml -i inventory.yaml -K

# Bootstrap VMs
ansible-playbook playbooks/bootstrap-vms.yaml -i inventory.yaml -K

# Remove a tenant
ansible-playbook playbooks/removeuser.yaml -i inventory.yaml
```

**Note:** The `-K` flag prompts for sudo password. Required on first run; passwordless sudo is configured automatically afterward.

### Verifying VM Access

SSH to a VM using proxy jump:
```bash
ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
  -J <admin-user>@restsrv01.polito.it \
  <vm-user>@restvm-<vm-user>-01
```

## Important Implementation Notes

### IP Address Management
- Each VM requires exactly 2 consecutive IPs from `10.10.0.0/24`
- IPs must include `/24` CIDR notation in `dataplane_ipv4` array
- Check `playbooks/README.md#list-of-ip-addresses-in-use` before allocating
- The `p4tenant` tool scans `host_vars/restvm-*.yaml` files to find available IPs

### YAML Configuration Requirements
- `host_users` in VM host_vars MUST be a list (use `-` prefix) even for a single user
- `dataplane_ipv4` must be an array with CIDR notation (e.g., `["10.10.0.21/24", "10.10.0.22/24"]`)
- VM naming convention: `restvm-{username}-{nn}` where nn is zero-padded (01, 02, etc.)

### Ansible Configuration
- Host key checking disabled (`ansible.cfg`)
- SSH agent forwarding enabled for cloning private repos
- VMs require ProxyCommand in inventory to route through `restsrv01`

### Role Dependencies
The `kvm_provision` role requires running `kvm-pre` and `kvm-debian-bridged-net-pre` roles first. The `adduser.yaml` playbook handles this ordering correctly.

### P4 SDE Environment
VMs are provisioned with P4 SDE at `/opt/p4-sde/bf-sde-9.13.2`. Environment variables `SDE` and `SDE_INSTALL` are configured globally. Users have access to convenience scripts: `p4-build`, `sde`, `p4`, `iftofinoup/iftofinodown`, `tfm`, `switch-intel`.

### Current Configuration State
As of the latest commit, the cluster serves these users: `zhihaow`, `pgiaccone`, `asacco`, `aangi`, `mamanj`, `mspina`. The switch `rest-bfsw02` is primarily targeted by bootstrap playbooks (to target both switches, edit the playbook's `hosts:` line to `p4switches`).

### Backup System
The p4tenant tool creates backups in `.p4tenant-backups/` before modifying any configuration files. These backups are timestamped and can be used for recovery.
