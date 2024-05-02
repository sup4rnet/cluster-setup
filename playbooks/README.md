# SUPER P4 VM - Ansible automation

## Requirements

* Ansible client installed (tested with v2.13.7) on your machine.
* SSH access with sudo permissions to Ansible targets

The following Ansible targets are possible:

* Physical servers e.g., `restsrv01`
* P4 switch control-plane CPUs
* Virtual machines

## Ansible playbooks

* `debian-kvm-p4dev-vm.yaml`: creates a new KVM virtual machine with P4 SDE
* `adduser-interactive.yaml`: adds a single user to the target (interactive prompt).
* `p4dev-bootstrap.yaml`: adds users, configures network and add some SDE utilities

## 1) Create a VM for a new user

This role creates a new `libvirt` VM cloning a base VM with P4 development environment installed.
* Add the VM hostname to the `vms` Ansible variable in `host_vars/restsrv01.yaml`

From your Ansible client run the playbook:
```
ansible-playbook playbooks/debian-kvm-p4dev-vm.yaml -i inventory.yaml
```

## 2) Managing tenants and P4 development environment

Both Edgecore Wedge100BF-32X P4 switches feature a control-plane CPU running Ubuntu 20.04 and different tenants are mapped to different Linux users. User's read/write permissions are limited to their home directory and root execution is granted for a minimal set of commands.

On the `restsrv01.polito.it` server, every tenant can ask one or more personal VMs with sudo permissions and Intel P4 development environemnt.

The role `p4dev-bootstrap.yaml` realizes the previous configuration: 
* on `p4switches`: it adds all users to the control-plane OS running in the Wedge100BF-32X switches, and configures [P4 SDE dev utilities](../README.md#p4-development-environment-and-utilities).

* on `vms`: it configures the VM's tenant user, the [P4 SDE dev utilities](../README.md#p4-development-environment-and-utilities) and assigns [static IP addresses](../README.md#vm-installation-with-ansible-playbooks) to the dataplane network.

### How to run


* Add the VM you just created as a new Ansible target (`inventory.yaml`). 

* Create a new file `<VM hostname>.yaml` under `host_vars` folder, to set VM-specific Ansible variables. Note: the name should match the VM name you previously set in `host_vars/restsrv01.yaml`.

* In `/host_vars/<VM hostname>.yaml` set the following variables:
    - `tenant_username`: VM's intended user (a new user with sudo permissions will be configured on the VM)
    - `vm_dataplane_ipv4`: your VM's dataplane IP address in the subnet `10.10.0.0/24`.


Run:

```
ansible-playbook playbooks/p4dev-vm-bootstrap.yaml -i inventory.yaml -K
```

The `-K` option will prompt for the `sudo` password and is required only the first time you run this playbook on a newly created VM.