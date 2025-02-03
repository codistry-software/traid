# tests/ml/models/test_base_model.py
import pytest
import tensorflow as tf
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


def test_model_building():
    """Test if model properly builds with TensorFlow layers."""

    class TestModel(BaseModel):
        def build(self, input_shape):
            self.model = tf.keras.Sequential([
                tf.keras.layers.Dense(32, input_shape=input_shape, activation='relu'),
                tf.keras.layers.Dense(1)
            ])
            self.model.compile(optimizer='adam', loss='mse')

        def get_config(self):
            return {'units': 32}

    model = TestModel()
    model.build(input_shape=(10,))

    # Verify TensorFlow model properties
    assert isinstance(model.model, tf.keras.Sequential)
    assert len(model.model.layers) == 2
    assert model.model.input_shape == (None, 10)
    assert model.model.output_shape == (None, 1)