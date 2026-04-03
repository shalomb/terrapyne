#!/usr/bin/env python3
"""Example: Parse a plain text terraform plan output.

This demonstrates how to extract structured data from a plain text plan,
which is common when working with TFC remote backends.
"""

from terrapyne import Terraform


def main():
    # Sample plan text (typically you'd read this from a file or TFC API logs)
    plan_text = """
Terraform will perform the following actions:

  # aws_instance.web will be created
  + resource "aws_instance" "web" {
      + ami           = "ami-12345"
      + instance_type = "t2.micro"
      + tags          = {
          + "Environment" = "dev"
        }
    }

Plan: 1 to add, 0 to change, 0 to destroy.
    """

    # Option 1: Use the Terraform class method
    tf = Terraform(".")
    result = tf.parse_plain_text_plan(plan_text)

    # Option 2: Use the PlanParser directly
    # parser = PlanParser(plan_text)
    # result = parser.parse()

    print("--- Plan Summary ---")
    summary = result.get("plan_summary", {})
    print(f"To Add:     {summary.get('add', 0)}")
    print(f"To Change:  {summary.get('change', 0)}")
    print(f"To Destroy: {summary.get('destroy', 0)}")
    print(f"Status:     {result.get('plan_status')}")

    print("\n--- Resource Changes ---")
    for rc in result.get("resource_changes", []):
        address = rc.get("address")
        actions = rc.get("change", {}).get("actions", [])
        print(f"Resource: {address} (Actions: {', '.join(actions)})")

        # Access attributes
        after = rc.get("change", {}).get("after", {})
        if after:
            print(f"  AMI: {after.get('ami')}")
            print(f"  Tags: {after.get('tags')}")


if __name__ == "__main__":
    main()
