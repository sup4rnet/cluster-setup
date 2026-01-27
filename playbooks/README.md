# Playbook description

Ansible playbooks to add new tenants (users and VMs) to the SUPERNET cluster.

## Overview

### Requirements

* Ansible client installed (tested with v2.13.7) on your machine
* SSH access with sudo permissions to Ansible targets
* Your SSH public key at `~/.ssh/id_rsa.pub` (will be copied to targets)

### Ansible targets

* **servers**: Physical server `restsrv01` hosting the VMs
* **p4switches**: Control-plane CPUs on Tofino switches (`rest-bfsw01`, `rest-bfsw02`)
* **vms**: Tenant virtual machines (accessed via SSH proxy through `restsrv01`)

### Available playbooks

| Playbook | Purpose |
|----------|---------|
| `adduser.yaml` | **Full onboarding** - creates VM, configures P4 switches, bootstraps VM (recommended) |
| `removeuser.yaml` | **Full offboarding** - deletes VMs and removes user from all systems |
| `kvm-bridged-net.yaml` | Creates KVM VMs with bridged network interface |
| `kvm-sriov-net.yaml` | Creates KVM VMs with SR-IOV for high-performance networking |
| `bootstrap-tofino.yaml` | Configures users and P4 SDE on Tofino switches |
| `bootstrap-vms.yaml` | Configures networking and P4 SDE utilities on VMs |
| `update-dashboard.yml` | Updates SSH access control mechanism on switches |

### Automated CLI Tool

For a streamlined experience, use the **p4tenant CLI** which automates both adding and removing tenants:

```bash
./p4tenant-cli add      # Interactive tenant creation
./p4tenant-cli remove   # Interactive tenant removal
./p4tenant-cli list     # Show all tenants
```

See [p4tenant/README.md](../p4tenant/README.md) for full documentation.

---

## Tutorial: Adding a New Tenant

This tutorial walks through adding a new user "jdoe" with their own VM "restvm-jdoe-01".

### Step 1: Add username to the global user list

Edit `group_vars/all.yaml` and add the username to `restart_users`:

```yaml
restart_users:
  - zhihaow
  - pgiaccone
  - asacco
  - aangi
  - mamanj
  - mspina
  - jdoe        # <-- add new user here
```

This list is used by both P4 switches and the reservation webapp.

### Step 2: Add VM to the server's VM list

Edit `host_vars/restsrv01.yaml` and add the VM name:

```yaml
vms:
  - restsrv01-smartdata01
  - restvm-dauin-01
  - restsrv01-smartdata02
  - restvm-mamanj-01
  - restvm-mspina-01
  - restvm-jdoe-01    # <-- add new VM here
```

### Step 3: Create host variables file for the new VM

Create `host_vars/restvm-jdoe-01.yaml` with:

```yaml
# Dataplane IP addresses - pick UNUSED addresses from 10.10.0.0/24
# Check the "IP addresses in use" table below before choosing!
dataplane_ipv4:
  - 10.10.0.21/24    # <-- first dataplane interface
  - 10.10.0.22/24    # <-- second dataplane interface

# Users who will have accounts on this VM (MUST be a list, even for one user)
host_users:
  - jdoe
```

**Important**:
- `dataplane_ipv4` must include the `/24` CIDR notation
- `host_users` must be a YAML list (use `-` prefix) even for a single user

### Step 4: Add VM to the Ansible inventory

Edit `inventory.yaml` and add the VM under the `vms` group:

```yaml
vms:
    hosts:
        restsrv01-smartdata01:
            ansible_host: restsrv01-smartdata01
            ansible_user: p4-restart
        restvm-dauin-01:
            ansible_host: restvm-dauin-01
            ansible_user: p4-restart
        restvm-jdoe-01:                          # <-- add new VM
            ansible_host: restvm-jdoe-01
            ansible_user: p4-restart
    vars:
        ansible_ssh_common_args: '-o ProxyCommand="ssh <your-username>@restsrv01.polito.it -W %h:%p"'
```

**Note**: Replace `<your-username>` with your actual username for the SSH proxy.

### Step 5: Run the playbook

Option A - **Full onboarding** (recommended, does everything):
```bash
ansible-playbook playbooks/adduser.yaml -i inventory.yaml -K
```

Option B - **Step by step** (if you need more control):
```bash
# 1. Create the VM
ansible-playbook playbooks/kvm-bridged-net.yaml -i inventory.yaml

# 2. Add user to P4 switches
ansible-playbook playbooks/bootstrap-tofino.yaml -i inventory.yaml -K

# 3. Configure the VM
ansible-playbook playbooks/bootstrap-vms.yaml -i inventory.yaml -K
```

**About the `-K` flag**: Prompts for sudo password. Required on first run; after that, passwordless sudo is configured automatically.

### Step 6: Verify

SSH into the new VM:
```bash
ssh -J <your-username>@restsrv01.polito.it jdoe@restvm-jdoe-01
```

---

## Using Tags with adduser.yaml

The `adduser.yaml` playbook supports tags to run specific stages:

```bash
# Only create VMs (skip switch and VM bootstrap)
ansible-playbook playbooks/adduser.yaml -i inventory.yaml --tags kvmconf

# Only configure P4 switches
ansible-playbook playbooks/adduser.yaml -i inventory.yaml --tags p4conf -K

# Only bootstrap VMs
ansible-playbook playbooks/adduser.yaml -i inventory.yaml --tags vmboot -K

# Only add users to server and webapp database
ansible-playbook playbooks/adduser.yaml -i inventory.yaml --tags srvuseradd -K
```

---

## Removing a Tenant

This section describes how to remove a tenant manually. For automated removal, use `./p4tenant-cli remove`.

### Option A: Using the removeuser.yaml playbook (recommended)

The `removeuser.yaml` playbook handles the complete removal process:

```bash
ansible-playbook playbooks/removeuser.yaml -i inventory.yaml
```

The playbook will:
1. Prompt for the username to delete
2. Auto-discover all VMs containing that username
3. Shutdown and delete the VMs from libvirt
4. Delete the VM disk images
5. Remove the user from P4 switches
6. Remove the user from the webapp database
7. Remove the user from the physical server

You can also pass variables to skip prompts:
```bash
ansible-playbook playbooks/removeuser.yaml -i inventory.yaml \
  -e user_to_delete=jdoe \
  -e confirm_deletion=DELETE
```

### Option B: Manual step-by-step removal

If you prefer manual control, follow these steps:

#### Step 1: Delete the VM

SSH into `restsrv01` and run:
```bash
# Shutdown the VM
virsh shutdown restvm-jdoe-01

# Wait for shutdown, then undefine
virsh undefine restvm-jdoe-01

# Delete the disk image
sudo rm /var/lib/libvirt/images/ubuntu20.04-p4-sde-restvm-jdoe-01.qcow2
```

#### Step 2: Remove user from P4 switches

SSH into each switch (`rest-bfsw01`, `rest-bfsw02`) and run:
```bash
sudo userdel -r jdoe
```

#### Step 3: Remove user from webapp database

On `restsrv01`, edit the users file:
```bash
sudo sed -i '/^jdoe$/d' /opt/tofino-rsvp/webapp/.data/users.csv
```

#### Step 4: Remove user from physical server

On `restsrv01`:
```bash
sudo userdel -r jdoe
```

#### Step 5: Update configuration files

Remove the tenant from these files:
- `group_vars/all.yaml` - Remove username from `restart_users` list
- `host_vars/restsrv01.yaml` - Remove VM name from `vms` list
- `host_vars/restvm-jdoe-01.yaml` - Delete this file
- `inventory.yaml` - Remove VM entry from `vms.hosts`
- `inventory-*.yaml` - Remove VM entry from any admin-specific inventories

---

## About the P4 Switches

Both P4 switches (`rest-bfsw01`, `rest-bfsw02`) have control-plane CPUs running Ubuntu 20.04. Each tenant gets a Linux user account with:

- Read/write permissions limited to their home directory
- Restricted sudo access for P4-related commands only (compiling, running switchd, etc.)
- Access to [P4 SDE utilities](../README.md#p4-development-environment-and-utilities)

The `bootstrap-tofino.yaml` playbook configures this environment.

**Note**: Currently `bootstrap-tofino.yaml` targets only `rest-bfsw02`. To run on both switches, edit the `hosts:` line in the playbook to `p4switches`.


---

## List of IP addresses in use

Static configuration is temporary (to be replaced with DHCP in the future).

**Pick an IP address NOT listed below** (each VM needs 2 consecutive IPs):

| IP address | Hostname | Description | Contact |
| --- | --- | --- | --- |
| `10.10.0.2` | `rest-bfsw01` | Tofino internal CPU Ethernet port | alessandro.cornacchia@polito.it
| `10.10.0.3` | `rest-bfsw01` | Tofino internal CPU Ethernet port | "
| `10.10.0.4` | `rest-bfsw02` | Tofino internal CPU Ethernet port | "
| `10.10.0.5` | `rest-bfsw02` | Tofino internal CPU Ethernet port | "
| `10.10.0.10` | `restsrv01` | Dataplane port@bridge `enp5s0@br0` | "
| `10.10.0.101` | `restsrv01` | Dataplane port `ens5f1@br1` | "
| `10.10.0.11` | `restsrv01-smartdata01` | User VM | zhihao.wang@polito.it
| `10.10.0.12` | `restsrv01-smartdata01` | User VM | zhihao.wang@polito.it
| `10.10.0.13` | `restvm-dauin-01` | User VM | asacco, aangi
| `10.10.0.14` | `restvm-dauin-01` | User VM | asacco, aangi
| `10.10.0.15` | `restvm-ojasson-01` | User VM | s321275@studenti.polito.it
| `10.10.0.16` | `restvm-ojasson-01` | User VM | s321275@studenti.polito.it
| `10.10.0.17` | `restsrv01-smartdata02` | User VM | zhihao.wang@polito.it
| `10.10.0.18` | `restsrv01-smartdata02` | User VM | zhihao.wang@polito.it
| `10.10.0.19` | `restvm-mamanj-01` | User VM | amanj.malaei@studenti.polito.it
| `10.10.0.20` | `restvm-mamanj-01` | User VM | amanj.malaei@studenti.polito.it

