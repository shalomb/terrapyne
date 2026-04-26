terraform {
  cloud {
    organization = "my-org"

    workspaces {
      tags = ["app", "production"]
    }
  }
}
