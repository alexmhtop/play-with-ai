variable "vault_addr" {
  description = "Vault address, e.g. http://127.0.0.1:8200"
  type        = string
}

variable "vault_token" {
  description = "Vault token with permissions to configure secrets"
  type        = string
  sensitive   = true
}

variable "kv_path" {
  description = "Path to mount the KV engine"
  type        = string
  default     = "kv"
}

variable "database_url" {
  description = "Database URL to store in Vault for the app"
  type        = string
}

variable "books_api_client_secret" {
  description = "Keycloak client secret for books-api"
  type        = string
  sensitive   = true
}
