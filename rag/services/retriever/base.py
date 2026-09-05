from abc import ABC, abstractmethod
from typing import Any

class BaseRetriever(ABC):

    def _data(self, response: Any) -> list[dict[str, Any]]:
        result = getattr(response, "data", response)
        return result if isinstance(result, list) else ([] if result is None else [result])

    @abstractmethod
    def retrieve(self, query: str):
        raise NotImplementedError("Subxlasses must implement retrieve method")
