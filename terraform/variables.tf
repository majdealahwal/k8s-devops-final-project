variable "subscription_id" {
  description = "Azure subscription ID"
  type        = string
}

variable "location" {
  type    = string
  default = "westeurope"
}

variable "resource_group_name" {
  type    = string
  default = "rg-k8slab"
}

variable "vnet_cidr" {
  type    = string
  default = "10.0.0.0/16"
  validation {
    condition     = can(cidrhost(var.vnet_cidr, 0))
    error_message = "vnet_cidr must be a valid CIDR, e.g. 10.0.0.0/16."
  }
}

variable "subnet_cidr" {
  type    = string
  default = "10.0.1.0/24"
  validation {
    condition     = can(cidrhost(var.subnet_cidr, 0))
    error_message = "subnet_cidr must be a valid CIDR, e.g. 10.0.1.0/24."
  }
}

variable "my_public_ip" {
  description = "Your laptop public IP in CIDR form, e.g. 203.0.113.5/32"
  type        = string
  validation {
    condition     = can(cidrhost(var.my_public_ip, 0))
    error_message = "my_public_ip must be a valid CIDR, e.g. 203.0.113.5/32."
  }
}

variable "vm_size" {
  type    = string
  default = "Standard_B2s"
}

variable "admin_username" {
  type    = string
  default = "azureuser"
}

variable "ssh_public_key_path" {
  type    = string
  default = "~/.ssh/k8slab_key.pub"
}

variable "nodes" {
  description = "Cluster nodes"
  type = map(object({
    hostname   = string
    private_ip = string
  }))
  default = {
    cp1 = { hostname = "k8slab-cp1", private_ip = "10.0.1.10" }
    w1  = { hostname = "k8slab-w1", private_ip = "10.0.1.11" }
  }
}