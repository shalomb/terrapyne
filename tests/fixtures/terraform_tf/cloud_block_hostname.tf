terraform {
  cloud {
    hostname     = "tfe.example.com"
    organization = "my-org"

    workspaces {
      name = "my-workspace"
    }
  }
}
