"""Tests for cloud_compatible component attribute."""

from lfx.custom.attributes import ATTR_FUNC_MAPPING, getattr_return_bool
from lfx.template.frontend_node.base import FrontendNode


class TestCloudCompatibleAttribute:
    """Tests that the cloud_compatible attribute flows through the metadata pipeline."""

    def test_cloud_compatible_in_attr_func_mapping(self):
        """cloud_compatible should be registered in ATTR_FUNC_MAPPING."""
        assert "cloud_compatible" in ATTR_FUNC_MAPPING
        assert ATTR_FUNC_MAPPING["cloud_compatible"] is getattr_return_bool

    def test_frontend_node_defaults_cloud_compatible_true(self):
        """FrontendNode should default cloud_compatible to True."""
        from lfx.template.template.base import Template

        node = FrontendNode(
            template=Template(type_name="test", fields=[]),
            base_classes=["Component"],
        )
        assert node.cloud_compatible is True

    def test_frontend_node_accepts_cloud_compatible_false(self):
        """FrontendNode should accept cloud_compatible=False."""
        from lfx.template.template.base import Template

        node = FrontendNode(
            template=Template(type_name="test", fields=[]),
            base_classes=["Component"],
            cloud_compatible=False,
        )
        assert node.cloud_compatible is False

    def test_frontend_node_serializes_cloud_compatible(self):
        """cloud_compatible should be present in serialized output."""
        from lfx.template.template.base import Template

        node = FrontendNode(
            template=Template(type_name="test", fields=[]),
            base_classes=["Component"],
            name="TestComponent",
            cloud_compatible=False,
        )
        serialized = node.to_dict(keep_name=False)
        assert "cloud_compatible" in serialized
        assert serialized["cloud_compatible"] is False

    def test_getattr_return_bool_handles_cloud_compatible(self):
        """getattr_return_bool should correctly process cloud_compatible values."""
        cloud_true = True
        cloud_false = False
        assert getattr_return_bool(cloud_true) is True
        assert getattr_return_bool(cloud_false) is False
        assert getattr_return_bool(None) is None
        assert getattr_return_bool("not a bool") is None
