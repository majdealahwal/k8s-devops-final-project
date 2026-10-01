# VM Specifications (Path B: VMware Workstation)

This project uses **Path B**: two Rocky Linux 9 virtual machines created manually in
VMware Workstation instead of Azure. The Terraform files are still formatted and
validated (`terraform fmt -check`, `terraform validate`).

## Virtual Machines

| Item | cp1 (Control Plane) | w1 (Worker) |
|------|---------------------|-------------|
| Hostname | `k8slab-cp1` | `k8slab-w1` |
| Kubernetes role | Control Plane | Worker Node |
| Ansible role | Controller | Managed Node |
| OS | Rocky Linux 9.8 (Blue Onyx) | Rocky Linux 9.8 (Blue Onyx) |
| vCPU | 2 | 2 |
| RAM | 4 GB | 4 GB |
| Disk | 40 GB | 40 GB |
| Network interface | `ens160` | `ens160` |
| Static IP | `10.0.1.10/24` | `10.0.1.11/24` |
| Default gateway | `10.0.1.2` | `10.0.1.2` |

## Network

- Hypervisor: VMware Workstation
- Network mode: NAT (VMnet8)
- Subnet: `10.0.1.0/24`
- Gateway: `10.0.1.2` (VMware NAT gateway)
- IP assignment: static (no DHCP), because Kubernetes nodes must keep stable addresses

## Automation User

- User: `majde` (member of the `wheel` group, passwordless sudo through `/etc/sudoers.d/majde`)

## Name Resolution (`/etc/hosts` on both nodes)

```
10.0.1.10  k8slab-cp1
10.0.1.11  k8slab-w1
```

## SSH Access

The laptop public key (`~/.ssh/k8slab_key.pub`) is installed on both nodes.

```bash
ssh -i ~/.ssh/k8slab_key majde@10.0.1.10   # cp1
ssh -i ~/.ssh/k8slab_key majde@10.0.1.11   # w1
```

## Verification

```bash
hostname
ip -br a
ip route | head -1
nproc
free -h | grep Mem
lsblk -d -o NAME,SIZE
ping -c 3 k8slab-w1     # from cp1
ping -c 3 k8slab-cp1    # from w1
```

Result: both nodes reply to ping by hostname with 0% packet loss, and SSH key login works
without a password prompt.
