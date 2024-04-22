## PoliTO RESTART P4 cluster

### Initial setup
Quick script to do the following:
* adds users defined in `group_vars/all.yaml`
* adds sudoers permissions to `admin_user`

```
ansible-playbook bootstrap.yaml -i hosts -K
```

### Add single user (interactive mode)
To add a single user, either repeat above after modifying the file `group_vars/all.yaml` or run:

```
ansible-playbook adduser-interactive.yaml -i hosts
```

and you will be prompted for the username to add.

*NOTE:* these scripts assume an ansible "admin" user is already installed on the targets (check `ansible_user` in `hosts` inventory file)