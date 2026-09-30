output "public_ips" {
  value = { for k, v in azurerm_public_ip.pip : k => v.ip_address }
}

output "private_ips" {
  value = { for k, v in var.nodes : k => v.private_ip }
}

output "ssh_commands" {
  value = {
    for k, v in azurerm_public_ip.pip :
    k => "ssh -i ~/.ssh/k8slab_key ${var.admin_username}@${v.ip_address}"
  }
}