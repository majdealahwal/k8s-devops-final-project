# k8s-devops-final-project

**End-to-End Infrastructure, Ansible, Kubernetes & CI/CD**

Author: **Majde Wannees Alahwal**
Infrastructure path: **Path B (VMware Workstation)**. I had no Azure subscription, so `terraform apply` was not run. The Terraform code was formatted and validated.

---

## 1. Project Overview

This project builds an automated container platform. Two Rocky Linux 9 VMs are configured with Ansible. A Kubernetes cluster with Calico CNI is bootstrapped "in one shot" with `site.yml`. A Flask + PostgreSQL application (Task Tracker) is tested, built, and published to GitHub Container Registry (GHCR) by GitHub Actions, and then deployed on the cluster.

### Cluster

| Node | Hostname | Role | Ansible role | Private IP |
|------|----------|------|--------------|-----------|
| cp1 | `k8slab-cp1` | Control Plane | Controller (local connection) | `10.0.1.10` |
| w1 | `k8slab-w1` | Worker | Managed node (SSH) | `10.0.1.11` |

- Network: VMware **NAT**, subnet `10.0.1.0/24`, gateway `10.0.1.2`. Details are in [`docs/vm-specs.md`](docs/vm-specs.md).
- Automation user: `majde` (member of `wheel`, passwordless sudo through `/etc/sudoers.d/majde`).

### Versions used

| Component | Version |
|-----------|---------|
| Kubernetes | v1.36.5 |
| containerd | 2.3.6 |
| Calico CNI | v3.31.0 |
| ansible-core (on cp1) | 2.14.18 |
| Terraform (laptop) | v1.16.4 |
| Python (laptop) | 3.13.2 |
| Docker image base | `python:3.12-slim` |
| PostgreSQL | 16 |

### Repository structure

```text
k8s-devops-final-project/
├── terraform/        # providers, variables, network, vms, outputs (validated only)
├── ansible/          # inventory.ini, group_vars/, playbooks, site.yml
├── app/              # Flask Task Tracker, Dockerfile, tests, scripts/seed.py
├── k8s/              # PostgreSQL and application manifests
├── docs/
│   ├── vm-specs.md
│   └── screenshots/
├── .github/workflows/ci-cd.yml
├── docker-compose.yml
└── README.md
```

---

## 2. Quick Start: Reproduction Commands

**Requirements:** two Rocky Linux 9 VMs (2 vCPU, 4 GB RAM, 40 GB disk each), a NAT network `10.0.1.0/24`, a user `majde` with sudo, and SSH key login. See `docs/vm-specs.md`.

### Step 1: Clone the repository (laptop)
```bash
git clone https://github.com/majdealahwal/k8s-devops-final-project.git
cd k8s-devops-final-project
```

### Step 2: Validate Terraform (Path B, no `apply`)
```bash
cd terraform
terraform fmt -check
terraform init -backend=false
terraform validate
cd ..
```

### Step 3: Install Ansible on cp1 only, then clone the repository there
```bash
# on cp1 (k8slab-cp1) as user majde
sudo dnf install -y ansible-core git
ansible --version
cd /home/majde
git clone https://github.com/majdealahwal/k8s-devops-final-project.git
ls ~/k8s-devops-final-project
```
w1 has no Ansible installed because Ansible is agentless.

### Step 4: Test connectivity and prepare the nodes
```bash
cd ~/k8s-devops-final-project/ansible       # run all commands from the ansible/ folder
ansible -i inventory.ini k8s_cluster -m ping
ansible -i inventory.ini k8s_cluster -b -m command -a "whoami"
ansible-playbook -i inventory.ini prepare-nodes.yml
```

### Step 5: Build the Kubernetes cluster in one shot
```bash
ansible-playbook -i inventory.ini site.yml
kubectl get nodes -o wide
```
`site.yml` runs the playbooks in this order: `prerequisites.yml`, `containerd.yml`, `kubernetes.yml`, `control-plane.yml`, `workers.yml`. Both nodes must show `Ready`.

### Step 6: Run the application tests and the seed script (laptop, Windows PowerShell)
```powershell
cd app
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python -m pytest -v            # expected: 7 passed
python scripts/seed.py         # adds 10 sample tasks
```

### Step 7: Run with Docker Compose (laptop)
```bash
# from the project root
docker compose up -d --build
docker compose ps
curl http://localhost:5000/ready      # expected: {"status":"ready"}
```
In PowerShell, use `curl.exe` instead of `curl`.

### Step 8: Deploy on Kubernetes (cp1)
```bash
cd ~/k8s-devops-final-project
kubectl apply -f k8s/
kubectl get pods,svc -o wide
```
Open the application in the browser: `http://10.0.1.10:30500`

### Step 9: CI/CD (automatic)
Every push to `main` runs `.github/workflows/ci-cd.yml`:
1. Lint (flake8) and unit tests (pytest)
2. `terraform validate`
3. Build the Docker image and push it to GHCR with the `latest` tag and the commit SHA tag

### Step 10: Teardown (Path B)
```bash
# on each VM
sudo shutdown -h now
```

### Step 11: Bonus 2, remote kubectl from the laptop (Windows PowerShell)
```powershell
winget install -e --id Kubernetes.kubectl
kubectl version --client

mkdir $HOME\.kube -Force
scp -i $HOME\.ssh\k8slab_key majde@10.0.1.10:~/.kube/config $HOME\.kube\config

kubectl get nodes -o wide
kubectl cluster-info
kubectl get pods,svc -o wide
```
The kubeconfig file has full `cluster-admin` rights. I keep it in `C:\Users\HP\.kube\`, **outside the repository**, and never push it to Git.

---

## 3. Technical Questions

### Part A: Repository & Workstation Setup

**Task 1, Question 1:** Which files did you exclude with `.gitignore`, and what sensitive data would they leak if committed?

**Answer:** I excluded five groups of files:
1. `*.tfstate*` (Terraform state). It stores resource IDs, IP addresses, and sometimes secrets in plain text. It is a full map of my infrastructure.
2. `.terraform/`. It holds local provider plugins. It is not secret, but it is big and useless in Git.
3. `terraform.tfvars`. It has my real values, such as the subscription ID and the admin username. I only commit `terraform.tfvars.example` with fake values.
4. Private SSH keys (for example `k8slab_key`). Anyone with this file can log in to my servers without a password.
5. `kubeconfig` and `admin.conf`. They contain the API address and certificates with full `cluster-admin` rights. Anyone with them controls the whole cluster.

**Task 1, Question 2:** If a secret is committed and deleted in a later commit, is it safe? Why or why not?

**Answer:** **No, it is not safe.** Git keeps the full history, and every commit is a permanent snapshot. Anyone can see the old secret with `git log` or `git show`, and every clone of the repository contains the whole history. The correct fix is to **revoke or rotate the secret immediately** (create a new one and cancel the old one). Removing it from history needs tools such as `git filter-repo` or BFG, but rotating the secret is the real solution.

**Task 2, Question:** How does Terraform authenticate to Azure in this setup, and why is this method safer than hardcoding credentials inside `.tf` files?

**Answer:** Terraform uses the **Azure CLI login**. I run `az login` once, and Terraform uses that session token. The `.tf` files only contain the subscription ID, passed as a variable. This is safer because:
- No password or secret is written in the code, so nothing can leak to GitHub.
- The token is temporary and can be revoked.
- Each person uses their own login, so there are no shared secrets.

*Note: I used Path B (VMware), so `terraform apply` was not run. This answer describes the Azure setup from the assignment.*

### Part B: Infrastructure as Code

**Task 3, Question:** What happens if you run `terraform apply` before accepting the marketplace terms?

**Answer:** The apply **fails when it tries to create the VMs**. Azure returns an error saying that the legal terms of the image (Rocky Linux 9) are not accepted. Network resources such as the resource group, VNet, and NSG may already be created, so the deployment is only partly done. The fix is to accept the terms first and then run `terraform apply` again.

**Task 4, Question:** What is the difference between a public key and a private key, and where does each reside?

**Answer:**
- The **private key** is secret. It stays only on my laptop (`~/.ssh/k8slab_key`). It proves my identity with a digital signature.
- The **public key** can be shared. It is placed on the VMs in `~/.ssh/authorized_keys`. The server uses it to verify my signature.
- The private key cannot be found from the public key. The public key is like a lock, and the private key is the only key that opens it.

**Task 5, Question 1:** Why does the NSG not need rules for Kubernetes traffic between cp1 and w1 inside the subnet?

**Answer:** Azure NSGs have a default rule called **`AllowVnetInBound`**. It allows all traffic inside the same VNet. cp1 and w1 are in the same subnet, so their traffic is already allowed. I only add rules for traffic from outside: SSH (22), the Kubernetes API (6443), and the application ports (80 and 5000).

**Task 5, Question 2:** Why must the private IPs be static for this cluster?

**Answer:** Kubernetes uses the IP addresses in many places: the API server certificate, `--apiserver-advertise-address`, the `kubeadm join` command, `/etc/hosts`, and the Ansible inventory. If an IP changes, these settings become wrong and the cluster breaks.

**Task 5, Question 3:** What is stored in `terraform.tfstate`, and why must it never be pushed to Git?

**Answer:** It stores the **current state of every resource** that Terraform manages: IDs, IP addresses, and all properties. Sometimes it also contains secrets in plain text. If it is pushed to Git, anyone can see my infrastructure and secrets. Git is also not safe for sharing state, because two people can overwrite each other.

### Part C: Secure Access & Automation Identity

**Task 7, Question 1:** Why does the user need passwordless sudo on cp1 as well, even though cp1 is the Ansible controller?

**Answer:** cp1 is the controller, but it is also a **managed node**. Ansible must install packages, edit files in `/etc`, and run `kubeadm` on cp1, and all of these need root. Ansible runs without a person at the keyboard, so it cannot type a password. With passwordless sudo, the playbooks run from start to end without stopping.

**Task 7, Question 2:** Why is a sudoers drop-in file safer than editing `/etc/sudoers` directly?

**Answer:**
- A syntax error in `/etc/sudoers` can break `sudo` for everyone, and I can lose root access.
- A drop-in file in `/etc/sudoers.d/` is separate. I can check it with `visudo -cf` before using it, and a mistake affects only that file.
- It is easy to add, remove, and audit one user, and system updates do not overwrite it.
- The file mode is `0440` (read-only), so nobody changes it by accident.

**Task 8, Question 1:** Why does `ssh-copy-id` fail on Azure VMs by default, and how did you install the key on w1?

**Answer:** Azure VMs have **password login disabled** by default. They accept only the SSH key that was added when the VM was created. `ssh-copy-id` needs to log in with a password first to copy the key, so it fails on Azure. On Azure, the solution is to copy the public key **manually** into `~/.ssh/authorized_keys` and then set the permissions (`chmod 700 ~/.ssh` and `chmod 600 ~/.ssh/authorized_keys`).

In my VMware lab, the Rocky Linux VMs allow password login, so `ssh-copy-id` worked. I ran this command from cp1 as user `majde`:

```bash
ssh-copy-id -i ~/.ssh/id_ed25519.pub majde@k8slab-w1
```

I entered the password of `majde` once. The command created `~/.ssh` and `authorized_keys` on w1 with safe permissions (700 and 600). After that, `ssh k8slab-w1 hostname` worked without a password.

**Task 8, Question 2:** What happens if permissions on `.ssh` or `authorized_keys` are configured too loosely?

**Answer:** The SSH server (`sshd`) **refuses to use the key** when other users can write to these files (the `StrictModes` check). Then the login falls back to a password or fails. It is also a security risk, because another user could add their own key and enter my account.

### Part D: Ansible Foundation

**Task 9, Question:** Why does w1 require no Ansible software installed? What does it need instead?

**Answer:** Ansible is **agentless**. The controller (cp1) sends small Python modules over SSH, runs them on w1, and removes them. So w1 only needs:
1. A running **SSH server** (`sshd`)
2. **Python 3**, because the modules run with Python
3. The controller's **public key** and a user with sudo

**Task 10, Question:** Why is cp1 managed with `ansible_connection=local` instead of connecting over SSH to itself?

**Answer:** cp1 is the machine that runs Ansible, so a **local connection** runs the tasks directly on it. An SSH connection to itself needs extra setup (a key for itself) and extra steps, and it can fail if `sshd` or the keys have a problem. A local connection is simpler, faster, and has fewer points of failure.

**Task 11, Question:** What does "idempotency" mean in Ansible and Infrastructure as Code?

**Answer:** Idempotency means that **running the same playbook many times gives the same final result**. The first run makes the changes. The next runs check the current state and change nothing, because the system is already correct. In this project, the final run of `prepare-nodes.yml` showed `changed=0` on both nodes. This also let me safely re-run the playbook only on w1 (`--limit k8slab-w1`) after an interrupted update.

### Part E: Kubernetes Cluster in "One Shot"

**Task 12, Question:** Why can the execution order of `control-plane.yml` and `workers.yml` never be swapped?

**Answer:** The control plane must be created **first**. `kubeadm init` on cp1 creates the API server, the certificates, and the join token. It also creates the **join command** that the worker needs. If `workers.yml` runs first, there is no API server to connect to and no join command, so the join fails.

**Task 13, Question 1:** Why does the Kubernetes kubelet refuse to run if SWAP is enabled?

**Answer:** Kubernetes gives each pod a memory request and limit, and the scheduler uses these numbers to place pods. With swap, the system can move memory pages to disk, so the real memory use is hidden and the limits are not reliable. Pods can become very slow and unpredictable. By default, the kubelet checks for swap and **refuses to start** (`failSwapOn=true`). That is why I run `swapoff -a` and remove the swap line from `/etc/fstab`, so swap stays off after a reboot.

**Task 13, Question 2:** Why must both containerd and kubelet use the same cgroup driver (systemd)?

**Answer:** cgroups are the Linux feature that limits CPU and memory for each container. On Rocky Linux, **systemd** is the init system and it already manages the cgroup tree. If containerd uses `cgroupfs` and kubelet uses `systemd`, two managers control the same resources. They can conflict, and the node becomes unstable. So both must use `systemd` (`SystemdCgroup = true` in `/etc/containerd/config.toml`).

**Task 14, Question:** Why is the control plane node in NotReady status until Calico CNI is applied?

**Answer:** The kubelet reports `Ready` only when the **pod network is ready**. This needs a CNI plugin and its configuration in `/etc/cni/net.d/`. `kubeadm init` builds the control plane, but it **does not install pod networking**. So the node stays `NotReady`, and the CoreDNS pods stay `Pending`. After Calico is applied, pods get IP addresses from `192.168.0.0/16` and the node changes to `Ready`.

### Part F: Application, Containerization & CI/CD

**Task 17, Question 1:** What is the advantage of using a slim Python base image compared to a standard image?

**Answer:**
- **Smaller size:** the slim image has only what Python needs.
- **Faster:** it builds, pushes to GHCR, and pulls to the Kubernetes node faster.
- **More secure:** fewer packages mean a smaller attack surface and fewer vulnerabilities to patch.
- The trade-off: slim has no compilers or extra tools, so sometimes I must install them myself.

**Task 17, Question 2:** What is the operational difference between the `/health` and `/ready` endpoints?

**Answer:**
- **`/health` (liveness)** answers "Is the app process alive?". If it fails, the platform **restarts** the container.
- **`/ready` (readiness)** answers "Can the app serve users now?". It checks that dependencies, such as the database, are reachable. If it fails, the platform **stops sending traffic** to this instance, but does not restart it.

---

## 4. Real Engineering Post-Mortems (Error → Cause → Fix)

### Post-Mortem 1: SSH key rejected because of a hidden BOM (Task 6B)

**Error:** SSH kept asking for a password, even after I installed my public key on the VM.

**Cause:** I copied the key from Windows with `type key.pub | ssh ...`. PowerShell added a hidden **UTF-8 BOM** (`EF BB BF`) at the start of the line in `authorized_keys`. So `sshd` could not read the line as a valid key and ignored it.

**Fix:** I removed the BOM with `sed 's/^\xEF\xBB\xBF//'`, removed duplicate lines with `sort -u`, set `chmod 600`, and ran `restorecon` for SELinux. After that, the key login worked. When a key looks correct but does not work, I now check hidden characters with `cat -A`.

### Post-Mortem 2: Web container restarting, psycopg2 vs psycopg3 (Task 17)

**Error:** After `docker compose up -d --build`, the `db` container was healthy, but `curl http://localhost:5000/ready` failed with "Failed to connect", and the `web` container kept restarting.

**Cause:** `DATABASE_URL` used the plain `postgresql://` format. SQLAlchemy then selected the **psycopg3** driver, but the image had **psycopg2** installed, so the application crashed at startup. I found this in `docker compose logs web`.

**Fix:** I changed the URL to `postgresql+psycopg2://` in `docker-compose.yml` and pinned `SQLAlchemy==2.1.4` in `requirements.txt`. Then `web` stayed Up and `/ready` returned `{"status":"ready"}`. I now read the container logs first and name the database driver in the URL.

### Post-Mortem 3: `git push` rejected because the remote was ahead (Task 16)

**Error:** After I committed my Task 16 work, `git push` was rejected: `! [rejected] main -> main (fetch first)`.

**Cause:** The GitHub repository had commits that my local copy did not have. Git refuses to push in this case, because the push would overwrite the remote history. This is a safety check, not a bug.

**Fix:** I ran `git pull --rebase`. Git downloaded the remote commits and put my new commit on top of them, and then `git push` worked. I did not use `git push --force`, because it would delete the remote commits.

---

## 5. Security Notes

- No secrets are committed. Terraform state, the real `terraform.tfvars`, private SSH keys, and `kubeconfig` / `admin.conf` are excluded by `.gitignore`.
- The private IPs (`10.0.1.x`) are internal lab addresses.
- Bonus 1 (third node `w2`) was not implemented.
