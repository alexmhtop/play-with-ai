variable "kc_url" {
  description = "Base URL for the Keycloak instance (e.g., http://localhost:8080)."
  type        = string
}

variable "kc_admin_client_id" {
  description = "Admin client id (usually admin-cli)."
  type        = string
}

variable "kc_admin_username" {
  description = "Admin username for password grant."
  type        = string
}

variable "kc_admin_password" {
  description = "Admin password for password grant."
  type        = string
  sensitive   = true
}

variable "realm" {
  description = "Realm name to manage."
  type        = string
  default     = "books"
}

variable "client_id" {
  description = "OIDC client id for the API."
  type        = string
}

variable "client_secret" {
  description = "OIDC client secret for confidential client."
  type        = string
  sensitive   = true
}

variable "redirect_uris" {
  description = "Allowed redirect URIs for the API client."
  type        = list(string)
  default     = []
}

variable "web_origins" {
  description = "Allowed web origins for CORS."
  type        = list(string)
  default     = ["+"]
}

variable "demo_user_password" {
  description = "Initial password for demo user."
  type        = string
  sensitive   = true
  default     = "ChangeMe123!"
}
