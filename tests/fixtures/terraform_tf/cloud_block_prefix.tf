terraform {
  cloud {
    organization = "my-org"

    workspaces {
      prefix = "my-app-"
    }
  }
}
