terraform {
  required_version = ">= 1.5.0"
  required_providers {
    keycloak = {
      source  = "mrparkers/keycloak"
      version = "~> 4.1"
    }
  }
}

provider "keycloak" {
  client_id                = var.kc_admin_client_id
  username                 = var.kc_admin_username
  password                 = var.kc_admin_password
  url                      = var.kc_url
  realm                    = "master"
  tls_insecure_skip_verify = false
}
