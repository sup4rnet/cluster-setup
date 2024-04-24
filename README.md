
# Setup on restsrv01 machine

The server `restsrv01` hosts VMs available for experiments with the P4 switches in a shared testbed environment for different tenants. Every tenant can be allocated a personal VM. 

For access to VPN polito and creation of user account ask:
* alessandro.cornacchia@polito.it
* paolo.giaccone@polito.it

## User instructions
### Connect to VMs through SSH
Users can connect to VMs through `ssh`. VMs are not directly visible on the PoliTO network, but are reachable by using `restsrv01` as a proxy.

Connect via `ssh` using `restsrv01` as a jump proxy:

```
ssh -J <your user>@restsrv01.polito.it <your user>@10.10.0.11
```

For convenience, you may want to add the following lines to your `.ssh/config` file. Replace:

* `restsrv01-smartdata01` with a string you like
* `<VM user>` and `<proxy user>` with your username on the VM and on `restsrv01` (proxy server) respectively. Likely they are the same.

```
Host restsrv01-smartdata01
  HostName 10.10.0.11
  User <VM user>
  ProxyCommand ssh <proxy user>@restsrv01.polito.it -W %h:%p
```

You can then connect by only typing:
```
ssh restsrv01-smartdata01
```

### Connectivity to P4 switches/other VMs for experiments

All VMs are connected to the testbed DATAPLANE network `10.10.0.0/24` with a static IPs on this address space (i.e., every VM has a virtual interface "*bridged*" on the datapane network). 

Also the P4 switch control-plane CPUs are connected to this network via the internal Ethernet ports between the CPU and the Tofino ASIC. Therefore, you can use the dataplane network to exchange traffic between the VMs and the Tofino control plane CPU. 

## Admin instructions
A base VM image (qcow2 file) with default account `p4-restart` and Intel P4 Studio environment configured is available under `/opt/vms`.

The VMs must be reachable on the DATAPLANE network `10.10.0.0/24`. We connect new VMs to the following networks:

* **Bridged network** (aka "host mode"): bridge `br0` is configured on `restsrv01` and all VMs attach to it with one virtual interface (e.g., `enp7s0`).

* **NAT network (libvirt default)**: this NATed network is used to provide Internet access to the VMs. VMs interfaces associated with this network will not be reachable by the outside (behind NAT) but can initiate connections to the Internet and PoliTO network.

Sketch of the instructions used to setup the environment in the following:

### VM hypervisor and network setup

Trying to install KVM QEMU virtual machine in bridged mode. Need to install network bridge. 

Apparently many ways to configure Debian 12 networking https://www.liberiangeek.net/2024/02/set-up-static-ip-address-debian-12/

Manual bridge creation (no persistence):
```
# create bridge br0 and turn it up
sudo ip link add name br0 type bridge
sudo ip link set br0 up

# add interface ens5f0 to bridge br0
sudo ip link set ens5f0 master br0
```

Manual bridge tear-down:
```
ip link set ens5f0 nomaster
ip link delete bridge_name type bridge
```

Verify configuration (use one of the following):
```
sudo brctl show br0
sudo bridge link
sudo ip link show master br0
```


Persistent creation:
* with `/etc/network/interfaces` described at: https://wiki.debian.org/BridgeNetworkConnections
* with `/etc/systemd/network` at: https://wiki.debian.org/SystemdNetworkd#setting_up_a_network_bridge

### VM creation and configuration

Create a VM and add `br0` as a bridged network and the `default (NAT)` network. You can do this from `virt-manager` GUI. 

Make sure both virtual interfaces are in active state.

From within the VM, identify the virtual interface connected to `br0`. One easy way is to look at which interface has not been automatically assigned an IP address. Assume `enp7s0`, run the following.

Assign static IP address (check availability):
```
ip address add 10.10.0.11/24 dev enp7s0
```

Add routing rules:
```
ip route add 10.10.0.1 dev enp7s0
ip route add 10.10.0.0/24 via 10.10.0.1 dev enp7s0
```

### Ansible automation

TODO