# p4tenant

CLI tool for managing P4-RESTART tenants. Automates the tenant onboarding process with automatic IP allocation, YAML editing, and ansible integration.

## Quick Start (No Installation)

Just install `uv` once, then use the wrapper script:

```bash
brew install uv

# Run from repo root
./p4tenant-cli list
./p4tenant-cli add user      # Add a new user with VM(s)
./p4tenant-cli add vm        # Add a VM to an existing user
./p4tenant-cli ip-status
```

The wrapper uses `uv run` to execute directly from source - no caching, always runs the latest code.

## Alternative: Install Globally

If you prefer having `p4tenant` available system-wide:

```bash
# Using uv (fastest)
brew install uv
cd p4tenant && uv tool install -e .

# Or using pipx
brew install pipx && pipx ensurepath
cd p4tenant && pipx install -e .

# Then run from anywhere inside the repo
p4tenant list
```

To uninstall: `uv tool uninstall p4tenant` or `pipx uninstall p4tenant`

## Usage

All commands must be run from within the `p4-restart-polito` repository directory.

### Add a new user

Interactive mode:
```bash
p4tenant add user
```

Non-interactive mode:
```bash
p4tenant add user -u jdoe -A pgiaccone -y
```

Options:
- `-u, --username`: Username for the new tenant
- `-e, --email`: Email address (optional)
- `-n, --num-vms`: Number of VMs to create (default: 1)
- `-A, --admin`: Admin user for SSH/ansible operations (prompted if not provided)
- `-y, --yes`: Skip confirmation prompts
- `-a, --run-ansible`: Run ansible-playbook after adding

### Add a VM to an existing user

Interactive mode:
```bash
p4tenant add vm
```

Non-interactive mode:
```bash
p4tenant add vm -u jdoe -A pgiaccone -y
```

Options:
- `-u, --username`: Username of the existing user
- `-v, --vm-name`: Name for the new VM (auto-suggested if not provided)
- `-A, --admin`: Admin user for SSH/ansible operations
- `-y, --yes`: Skip confirmation prompts
- `-a, --run-ansible`: Run ansible-playbook after adding

The command will:
1. Show a list of existing users to select from
2. Show the user's existing VMs
3. Suggest a name for the new VM following the naming convention (e.g., `restvm-jdoe-02`)
4. Allocate IPs and create the VM configuration

### Apply/provision an existing tenant

Run ansible playbook for a user already in the configuration:
```bash
p4tenant apply mamanj
p4tenant apply mamanj -A pgiaccone    # specify admin
p4tenant apply mamanj -A pgiaccone -y # non-interactive
```

Use this to:
- Provision a VM for a user already in config files
- Re-run provisioning after configuration changes
- Apply updates to an existing tenant's VM

### Remove a tenant

Interactive mode (recommended):
```bash
p4tenant remove
```

With username:
```bash
p4tenant remove jdoe
```

Non-interactive mode:
```bash
p4tenant remove jdoe -A pgiaccone -y
```

Options:
- `-A, --admin`: Admin user for SSH/ansible operations
- `-y, --yes`: Skip confirmation prompts
- `-s, --skip-ansible`: Only update config files (don't delete VMs)
- `-c, --skip-config`: Only run ansible (don't update config files)

The remove command:
1. Shows a list of tenants to choose from (if username not provided)
2. Shows VMs owned by the tenant with checkboxes to select which to delete
3. Shows config files that will be updated and asks for confirmation
4. Prompts for admin user
5. Runs ansible to delete VMs and remove user from remote systems
6. Updates configuration files

For the manual workflow without p4tenant, see [playbooks/README.md](../playbooks/README.md#removing-a-tenant).

### List all tenants

```bash
p4tenant list
```

Shows all tenants with their configuration status across all 4 files:
- `users`: In `group_vars/all.yaml` restart_users
- `vms`: In `host_vars/restsrv01.yaml` vms list
- `inv`: In `inventory.yaml` vms.hosts
- `host`: Has `host_vars/restvm-{user}-01.yaml` file

### Show IP allocation status

```bash
p4tenant ip-status
```

Shows:
- IP range and reserved IPs
- Currently used IPs
- Available IPs and pairs
- IP to VM mapping

## What it does

When adding a tenant, the tool:

1. Asks for your admin username (for SSH access to restsrv01)
2. Validates the tenant username (3-16 chars, lowercase alphanumeric + underscore/hyphen)
3. Checks the username doesn't already exist
4. Allocates the next available consecutive IP pair (e.g., 10.10.0.11/24, 10.10.0.12/24)
5. Updates these files:
   - `group_vars/all.yaml` - Adds username to `restart_users`
   - `host_vars/restsrv01.yaml` - Adds VM name to `vms` list
   - `host_vars/restvm-{user}-01.yaml` - Creates new file with IPs and host_users
   - `inventory.yaml` - Adds VM to `vms.hosts`
   - `inventory-{admin}.yaml` - Syncs admin-specific inventory (if not the default admin)
6. Optionally runs ansible-playbook with a minimal inventory for fast execution

Backups are created in `.p4tenant-backups/` before any file is modified.

## Admin User Support

Each admin has their own inventory file (`inventory-{admin}.yaml`) with:
- Their SSH username for `restsrv01`
- Their ProxyCommand for VM access

When you add a tenant:
- The main `inventory.yaml` is always updated
- If you're not the default admin (from main inventory), your admin-specific inventory is also synced

This allows multiple admins to work with their own credentials while keeping all inventories in sync.

## Fast Ansible Execution

When running ansible-playbook for a new user, the tool creates a **minimal temporary inventory** containing:
- The `p4switches` group (both switches)
- The `servers` group (`restsrv01`) for VM provisioning
- Only the new VM being added (not all existing VMs)

This avoids processing all existing VMs, making ansible execution much faster.

The temporary inventory:
- Uses your admin username for SSH connections
- Is automatically cleaned up after execution
- Works on Windows, Linux, and macOS

## IP Allocation

- VM IP range: 10.10.0.11 - 10.10.0.100
- Reserved IPs: .2-.5 (switches), .10, .101 (server)
- IPs are allocated in consecutive pairs
- The tool scans existing `host_vars/restvm-*.yaml` files to find used IPs

## Interactive Help

Type `?` at any prompt to see detailed help:

```
Enter tenant username (? for help): ?
╭──────────────────────────────────────────────────────────────────────────────╮
│ Tenant Username                                                              │
│ The username for the new P4-RESTART tenant.                                  │
│ Requirements:                                                                │
│   - 3-16 characters long                                                     │
│   - Lowercase letters, numbers, underscores, or hyphens                      │
│   - Must start with a letter                                                 │
│                                                                              │
│ This will create:                                                            │
│   - A VM named restvm-{username}-01                                          │
│   - User account on the VM                                                   │
│   - Allocated IP addresses for the dataplane                                 │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## Example Sessions

### Adding a new user

```
$ p4tenant add user

╭──────────────────────────────────────────────────────────────────────────────╮
│ Add New P4-RESTART User                                                      │
│                                                                              │
│ This wizard will guide you through creating a new user.                      │
│ Type ? at any prompt to see detailed help.                                   │
╰──────────────────────────────────────────────────────────────────────────────╯

Select admin user (? for help)

  1. alessandro  new
  2. pgiaccone   has inventory
  3. zhihaow     has inventory
  4. Other (enter manually)

Choice (1): 2

ℹ Operating as admin: pgiaccone

Enter tenant username (? for help): jdoe
Enter email (optional) (? for help): john.doe@polito.it

How many VMs to create? (? for help) [1]: 1

Validating...
✓ Username 'jdoe' is available
✓ Allocated IPs: 10.10.0.21/24, 10.10.0.22/24

╭────────────────────────────── Changes to apply ──────────────────────────────╮
│   1.    group_vars/all.yaml           Add 'jdoe' to restart_users            │
│   2.    host_vars/restsrv01.yaml      Add 'restvm-jdoe-01' to vms list       │
│   3.    host_vars/restvm-jdoe-01.yaml [NEW] Create with dataplane_ipv4       │
│   4.    inventory.yaml                Add 'restvm-jdoe-01' to vms.hosts      │
│   5.    inventory-pgiaccone.yaml      Add 'restvm-jdoe-01' to vms.hosts      │
╰──────────────────────────────────────────────────────────────────────────────╯

Apply changes? [y/n]: y

Applying changes...
✓ Synced inventory-pgiaccone.yaml
✓ All changes applied successfully

Run ansible-playbook? [y/n]: y

Creating minimal inventory for faster execution...
Running: ansible-playbook playbooks/adduser.yaml -i /tmp/p4tenant-inv-xyz.yaml
...
✓ ansible-playbook completed successfully
```

### Adding a VM to an existing user

```
$ p4tenant add vm

╭──────────────────────────────────────────────────────────────────────────────╮
│ Add New VM for Existing User                                                 │
│                                                                              │
│ This wizard will guide you through adding a VM to an existing user.          │
│ Type ? at any prompt to see detailed help.                                   │
╰──────────────────────────────────────────────────────────────────────────────╯

Select admin user (? for help)

Choice (1): 2

ℹ Operating as admin: pgiaccone

Select user

  1. jdoe       (1 VM(s))
  2. mamanj     (1 VM(s))
  3. mspina     (1 VM(s))

Choice: 1
ℹ Selected user: jdoe

Existing VMs for jdoe:
  - restvm-jdoe-01

Enter VM name [restvm-jdoe-02]:

Validating...
✓ VM name 'restvm-jdoe-02' is available
✓ Allocated IPs: 10.10.0.23/24, 10.10.0.24/24

╭────────────────────────────── Changes to apply ──────────────────────────────╮
│   1.    host_vars/restsrv01.yaml      Add 'restvm-jdoe-02' to vms list       │
│   2.    host_vars/restvm-jdoe-02.yaml [NEW] Create with dataplane_ipv4       │
│   3.    inventory.yaml                Add 'restvm-jdoe-02' to vms.hosts      │
│   4.    inventory-pgiaccone.yaml      Add 'restvm-jdoe-02' to vms.hosts      │
╰──────────────────────────────────────────────────────────────────────────────╯

Apply changes? [y/n]: y

Applying changes...
✓ Synced inventory-pgiaccone.yaml
✓ All changes applied successfully
```
