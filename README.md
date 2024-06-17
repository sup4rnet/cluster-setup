# SUPERNET: the SUPER programmable P4 NETwork cluster

Set of Ansible automation script to deploy new Virtual Machines (VMs) within the experimental SUPER testbed within Politecnico di Torino. Each VM is configured with:

* Intel P4 Studio and Tofino switch model
* Network access to the dataplane network `10.10.0.0/24`

## Overview
The cluster might be subject to changes as new/current servers are integrated/replaced. In its current configuration contains one server `restsrv01.polito.it` equipped with Debian 12, which hosts tenants VMs (KVM libvirt + QEMU).

Two Intel Tofino P4 programmable switches `rest-bfsw01.polito.it` and `rest-bfsw02.polito.it`  are available.

<div align="center">
<img src="./.images/topo.jpg" alt="drawing" width="400"/>
</div>


The repository contains a set of playbooks to manage VMs for new users on the `restsrv01` node. 

Access to the VM is granted via `ssh` following [User's VM access guide](#user-access-to-vm).

### Network
Each VM will be assigned a virtual network interface directly attached to the dataplane network (bridged mode). This interface is intended for experiments with the Tofino devices. 

Internet connectivity to the VMs is provided through a second interface (NAT mode), and must be exclusively used for control operations e.g., install packages. Traffic generated on this interface is NOT routed through Tofino switches.

* [How to configure bridge interfaces on KVM](./roles/kvm_provision/README.md). 
* [Dataplane IP addresses in use](./playbooks/README.md#list-of-ip-addresses-in-use)

### P4 development environment and utilities
VMs are provisioned with Intel P4 Software Development Environment (version 9.13.2) installed under `/opt/p4-sde/bf-sde-9.13.2`. The following commands are available:

* `p4-build`: convenience script to build P4 programs
* `sde`: change directory to SDE directory
* `p4`: alias for `/opt/p4-sde/bf-sde-9.13.2/run_switchd.sh` 
* `iftofinoup`/`iftofinodown`: creates/destroys veth pairs to work with the Tofino Model
* `tfm`: alias for `/opt/p4-sde/bf-sde-9.13.2/run_tofino_model.sh`
* `switch-intel`: runs Intel Switch.p4, i.e., alias for `/opt/p4-sde/bf-sde-9.13.2/run_switchd.sh -p switch`

## Ansible playbooks
VM creation and account provisioning on all the machines is automated via our set of Ansible playbooks. 

Admin users can follow the [playbook documentation](./playbooks/README.md).

## User access to VM

Enabled users can connect to their VMs through `ssh`, from within PoliTO local network. For external users, VPN must be acrivated first. 

To access PoliTO VPN and creation of user account ask:
* alessandro.cornacchia@polito.it
* paolo.giaccone@polito.it

### Connect to VMs through SSH
VMs are not directly visible on the PoliTO network, but are reachable by using `restsrv01` as a bastion proxy.
You have two options to connect. 

1) Connect via ssh to `restsrv01.polito.it`, and from there connect via ssh to your VM:

```
ssh <your user>@restsrv01.polito.it
ssh <your user>@<vm hostname>
```

2) Single-step `ssh` using `restsrv01.polito.it` as a jump proxy:

```
ssh -J <your user>@restsrv01.polito.it <your user>@<vm hostname>
```

For convenience, you may want to add the following lines to your `.ssh/config` file. Replace:

```
Host <vm name>
  User <your user>
  ProxyCommand ssh <you user user>@restsrv01.polito.it -W %h:%p
```

You can then connect by only typing on your client:
```
ssh <vm name>
```

### Note about hostname resolution
The name `<vm name>` is only resolved locally at `restsrv01.polito.it` (thanks to `libvirt-nss` VM name resolution plugin). It cannot be resolved from other hosts outside `restsrv01.polito.it`, as no DNS records for the VMs exist.