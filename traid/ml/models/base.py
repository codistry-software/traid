from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseModel(ABC):
    """Base class for all ML models.

    Defines the interface that all ML models must implement.
    """

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