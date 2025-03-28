# Playbook description

Set of playbooks with (minimal) automation of the kick-off actions required to add new tenants to the cluster.

## Overview

### Requirements

* Ansible client installed (tested with v2.13.7) on your machine.
* SSH access with sudo permissions to Ansible targets

### Ansible targets

* Physical servers e.g., `restsrv01`
* P4 switch control-plane CPUs
* Virtual machines

### Ansible playbooks

* `debian-kvm-p4dev-vm.yaml`: creates a new KVM virtual machine with P4 SDE
<!-- * `adduser-interactive.yaml`: adds a single user to the target (interactive prompt). -->
* `p4dev-bootstrap-tofino.yaml`: loads kernel modules to work with Tofino ASIC. Adds users, configures CPU to Tofino [ethernet interfaces](../README.md#vm-installation-with-ansible-playbooks) and add some SDE utilities in the Tofino switches. Enables sudo for selected commands and prepares `sshd` groups for dynamic tenant access management.

* `p4dev-bootstrap-vms.yaml`: configures network interfaces and add some SDE utilities in the tenant's VMs

* `p4dev-bootstrap-srv.yaml`: this is mainly related to installing the web server application for access reservation

## 1) Create a new VM

This creates a new `libvirt` VM, cloning a base VM with P4 development environment installed.
* Add the VM name to the `vms` Ansible variable in `host_vars/restsrv01.yaml`

From your Ansible client run the playbook:
```
ansible-playbook playbooks/debian-kvm-p4dev-vm.yaml -i inventory.yaml
```

## 2) Bootstrap new users

### Actions on Tofino

Both P4 switches feature a control-plane CPU running Ubuntu 20.04. Each tenant is represented by a different Linux user. User's read/write permissions are limited to its owm home directory. Root privileges are allowed for the minimal set of commands (e.g., compiling and running a P4 application) which require interaction with DMA.

The role `p4dev-bootstrap-tofino.yaml` realizes the previous configuration, and configures [P4 SDE dev utilities](../README.md#p4-development-environment-and-utilities).

Add the desired user to the `users` variable in `group_vars/p4switches.yaml`. Then run:

```
ansible-playbook playbooks/p4dev-bootstrap-tofino.yaml -i inventory.yaml -K
```

### Actions on VM
On the `restsrv01.polito.it` server, every tenant can ask one or more personal VMs with sudo permissions and Intel P4 development environemnt.

Steps to configure the VM's for a new tenant:

* Add the VM you just created as a new Ansible target (`inventory.yaml`). 

* Create a new file `<VM hostname>.yaml` under `host_vars` folder, to set VM-specific Ansible variables. Note: the name should match the VM name you previously set in `host_vars/restsrv01.yaml`.

* In `/host_vars/<VM hostname>.yaml` set the following variables:
    - `tenant_username`: VM's intended user
    - `dataplane_ipv4`: your VM's [dataplane IP address](#list-of-ip-addresses-in-use) in the subnet `10.10.0.0/24`.


Run:

```
ansible-playbook playbooks/p4dev-bootstrap-vms.yaml -i inventory.yaml -K
```

**NOTE about -K option**: The `-K` option will prompt for the `sudo` password and is required only the first time you run this playbook on a newly created VM. After the first run, your ansible user will be configured by the bootstrap script not to be asked for pwd.


## List of IP addresses in use
Static configuration is temporary (and to be replaced/implemented via DHCP). 

Make sure ot pick an IP address NOT listed below:

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

