from abc import ABC, abstractmethod
class BaseIngestion(ABC):
    @abstractmethod
    def ingest(self, *args, **kwargs):
        raise NotImplementedError("Subclasses must implement ingest method")
