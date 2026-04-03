terraform {
  backend "remote" {
    organization = "my-org"

    workspaces {
      prefix = "my-app-"
    }
  }
}
