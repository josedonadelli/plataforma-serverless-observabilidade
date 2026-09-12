terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.92"
    }
  }
}


provider "aws" {
  region = "sa-east-1" # troque pela região que você usa
}
