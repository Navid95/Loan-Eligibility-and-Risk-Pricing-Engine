from dataclasses import dataclass

from rate_calculator.domain.value_objects import District, PostalCode


@dataclass(frozen=True)
class PostalCodeMapping:
    postal_code: PostalCode
    district: District
    region1: str
    region2: str
    region3: str
