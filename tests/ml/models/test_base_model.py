import pytest
from traid.ml.models.base import BaseModel


def test_base_model_interface():
    """Test if BaseModel defines required interface methods."""

    # Since BaseModel is abstract, create minimal concrete class for testing
    class TestModel(BaseModel):
        def build(self, input_shape):
            pass

        def get_config(self):
            return {}

    model = TestModel()

    # Check if required methods exist
    assert hasattr(model, 'build')
    assert hasattr(model, 'get_config')

    # Check if instantiating BaseModel directly raises error
    with pytest.raises(TypeError):
        BaseModel()