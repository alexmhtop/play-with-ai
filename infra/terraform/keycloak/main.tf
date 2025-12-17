resource "keycloak_realm" "this" {
  realm        = var.realm
  display_name = "Books Realm"
  enabled      = true

  access_code_lifespan = "5m"
}

resource "keycloak_openid_client" "api" {
  realm_id    = keycloak_realm.this.id
  client_id   = var.client_id
  name        = "Books API"
  enabled     = true
  access_type = "CONFIDENTIAL"

  standard_flow_enabled        = true
  direct_access_grants_enabled = true
  service_accounts_enabled     = true

  valid_redirect_uris = var.redirect_uris
  web_origins         = var.web_origins
  client_secret       = var.client_secret
}

data "keycloak_openid_client_service_account_user" "api" {
  realm_id = keycloak_realm.this.id
  client_id = keycloak_openid_client.api.id
}

resource "keycloak_role" "books_read" {
  realm_id = keycloak_realm.this.id
  name     = "books:read"
}

resource "keycloak_role" "books_write" {
  realm_id = keycloak_realm.this.id
  name     = "books:write"
}

resource "keycloak_group" "admins" {
  realm_id = keycloak_realm.this.id
  name     = "admins"
}

resource "keycloak_group_roles" "admins_roles" {
  realm_id = keycloak_realm.this.id
  group_id = keycloak_group.admins.id
  role_ids = [
    keycloak_role.books_read.id,
    keycloak_role.books_write.id
  ]
}

resource "keycloak_user" "demo" {
  realm_id = keycloak_realm.this.id
  username = "demo"
  enabled  = true
  email    = "demo@example.com"
  email_verified = true
  first_name = "Demo"
  last_name  = "User"
  required_actions = []

  initial_password {
    value     = var.demo_user_password
    temporary = false
  }
}

resource "keycloak_user_groups" "api_service_account_groups" {
  realm_id = keycloak_realm.this.id
  user_id = data.keycloak_openid_client_service_account_user.api.id
  group_ids = [keycloak_group.admins.id]
}

resource "keycloak_user_groups" "demo_group" {
  realm_id  = keycloak_realm.this.id
  user_id   = keycloak_user.demo.id
  group_ids = [keycloak_group.admins.id]
}

resource "keycloak_openid_user_realm_role_protocol_mapper" "realm_roles" {
  realm_id  = keycloak_realm.this.id
  client_id = keycloak_openid_client.api.id
  name      = "realm-roles"

  claim_name          = "realm_access.roles"
  multivalued         = true
  add_to_id_token     = true
  add_to_access_token = true
}

resource "keycloak_openid_audience_protocol_mapper" "aud" {
  realm_id  = keycloak_realm.this.id
  client_id = keycloak_openid_client.api.id
  name      = "aud"

  add_to_id_token          = true
  add_to_access_token      = true
  included_custom_audience = var.client_id
}

resource "keycloak_openid_client_default_scopes" "api_scopes" {
  realm_id       = keycloak_realm.this.id
  client_id      = keycloak_openid_client.api.id
  default_scopes = ["profile", "email"]
}
