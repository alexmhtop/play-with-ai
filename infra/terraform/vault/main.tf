terraform {
  required_providers {
    vault = {
      source  = "hashicorp/vault"
      version = "~> 4.4"
    }
  }

  required_version = ">= 1.7.0"
}

provider "vault" {
  address = var.vault_addr
  token   = var.vault_token
}

resource "vault_mount" "kv" {
  path        = var.kv_path
  type        = "kv"
  options     = { version = "2" }
  description = "KV store for app secrets"
}

resource "vault_kv_secret_v2" "books_api" {
  mount               = vault_mount.kv.path
  name                = "books-api/config"
  delete_all_versions = true

  data_json = jsonencode({
    database_url = var.database_url
    client_secret = var.books_api_client_secret
  })
}
