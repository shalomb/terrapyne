"""Tests for A9: Terraform accessible via terrapyne.local sub-namespace.

Success criteria:
- `terrapyne.local.Terraform` resolves to the class
- `from terrapyne import Terraform` still works but emits DeprecationWarning
- `Terraform` is NOT in `terrapyne.__all__`
"""

import warnings


class TestLocalNamespace:
    def test_terraform_accessible_via_local_submodule(self):
        import terrapyne.local

        assert hasattr(terrapyne.local, "Terraform")

    def test_terraform_class_importable_from_local(self):
        from terrapyne.local import Terraform

        assert Terraform is not None

    def test_terraform_not_in_top_level_all(self):
        import terrapyne

        assert "Terraform" not in terrapyne.__all__

    def test_top_level_terraform_import_emits_deprecation_warning(self):
        # Force re-evaluation of the deprecated attribute each time
        import terrapyne

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            cls = terrapyne.Terraform  # noqa: F841
        deprecation_warnings = [w for w in caught if issubclass(w.category, DeprecationWarning)]
        assert deprecation_warnings, (
            "Expected a DeprecationWarning when accessing terrapyne.Terraform"
        )
        assert (
            "terrapyne.local" in str(deprecation_warnings[0].message).lower()
            or "deprecated" in str(deprecation_warnings[0].message).lower()
        )

    def test_top_level_terraform_still_returns_correct_class(self):
        import terrapyne
        from terrapyne.local import Terraform

        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            cls = terrapyne.Terraform
        assert cls is Terraform
