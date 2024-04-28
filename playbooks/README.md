# SUPER P4 VM - Ansible automation

## Requirements

* SSH access with sudo permissions to physical servers and VM base image
(name of user with `sudo` priviledges can be configured in Ansible variable `admin_user` under `group_vars`)
* Ansible client installed (tested with v2.13.7) on your machine

## Ansible description
The following Ansible targets are possible:

* Physical servers e.g., `restsrv01`
* P4 switch control-plane CPUs
* Virtual machines

The following playbooks are available:

* `debian-kvm-p4dev-vm.yaml`: creates a new KVM virtual machine with P4 SDE
* `adduser-interactive.yaml`: adds a single user to the target (interactive prompt).
* `p4dev-vm-bootstrap.yaml`: adds all users listed in Ansible vars on the target.

## Roels to setup a new user VM

### VM creation
This role creates a new `libvirt` VM cloning a base VM with P4 development environment installed.
* Add the VM hostname to the `vms` Ansible variable in `host_vars/restsrv01.polito.it.yaml`
* Create a new file under `host_vars` with your VM hostname and .yaml extension. 
* Add your VM's IP address in the Ansible variable `vm_dataplane_ipv4: 10.10.0.11/24`.
* Add the list of users to be created in the VM in the variable `users`.

From your Ansible client run the playbook:
```
ansible-playbook playbooks/debian-kvm-p4dev-vm.yaml -i inventory.yaml
```

### VM initialization
This role adds the new user and configures VM networking. 

Add the hostname of the created VM to the Ansible inventory `inventory.yaml`. 
Then run:

```
ansible-playbook playbooks/p4dev-vm-bootstrap.yaml -i inventory.yaml -K
```

The `-K` option is required only the first time you run the playbook to ask for `sudo` permissions.