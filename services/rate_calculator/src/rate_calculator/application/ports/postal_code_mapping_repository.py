from abc import ABC, abstractmethod

from rate_calculator.domain.entities import PostalCodeMapping
from rate_calculator.domain.value_objects import PostalCode


class PostalCodeMappingRepository(ABC):
    @abstractmethod
    async def get(self, postal_code: PostalCode) -> PostalCodeMapping | None: ...
