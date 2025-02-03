from abc import ABC, abstractmethod
from typing import Dict, Any
import tensorflow as tf


class BaseModel(ABC):
    """Base class for all ML models.

    Defines the interface that all ML models must implement.
    """

    def __init__(self):
        """Initialize the base model."""
        self.model: tf.keras.Model = None

    @abstractmethod
    def build(self, input_shape: tuple) -> None:
        """Build the model architecture.

        Args:
            input_shape: Shape of input data
        """
        pass

    @abstractmethod
    def get_config(self) -> Dict[str, Any]:
        """Get model configuration.

        Returns:
            Dict containing model configuration
        """
        pass

    def summary(self) -> str:
        """Get model summary.

        Returns:
            String containing model architecture summary
        """
        if self.model is None:
            raise ValueError("Model not built yet. Call build() first.")
        return self.model.summary()