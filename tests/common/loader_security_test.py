from pathlib import Path
from unittest.mock import patch

import pytest
import torch

from laia.common.loader import BasicLoader, ObjectLoader


class PicklePayload:
    def __init__(self, marker):
        self.marker = str(marker)

    def __reduce__(self):
        return (write_marker, (self.marker,))


def write_marker(marker):
    Path(marker).write_text("unsafe", encoding="utf-8")


def test_pickle_payload_blocked_without_execution(tmp_path):
    marker = tmp_path / "executed"
    model = tmp_path / "untrusted.pt"
    torch.save(PicklePayload(marker), model)
    with pytest.raises(ValueError, match="Unsafe or unsupported"):
        BasicLoader().load(model)
    assert not marker.exists()


@pytest.mark.parametrize("module,name", [("os", "system"), ("builtins", "eval")])
def test_descriptor_cannot_import_or_call_arbitrary_code(tmp_path, module, name):
    model = tmp_path / "untrusted.pt"
    torch.save({"module": module, "name": name, "args": ["arbitrary code"]}, model)
    with patch("laia.common.loader.import_module") as import_module:
        with pytest.raises(ValueError, match="Untrusted model factory blocked"):
            ObjectLoader(model).load()
        import_module.assert_not_called()


def test_plain_weights_load_safely(tmp_path):
    model = tmp_path / "weights.pt"
    torch.save({"weight": torch.arange(4)}, model)
    assert torch.equal(BasicLoader().load(model)["weight"], torch.arange(4))


def test_legacy_objects_require_explicit_opt_in(tmp_path):
    model = tmp_path / "legacy.pt"
    torch.save(PicklePayload(tmp_path / "unused"), model)
    # This verifies the opt-in loader setting without executing a payload.
    with patch("laia.common.loader.torch.load", return_value="trusted") as load:
        assert BasicLoader(allow_unsafe_pickle=True).load(model) == "trusted"
    assert load.call_args.kwargs["weights_only"] is False
