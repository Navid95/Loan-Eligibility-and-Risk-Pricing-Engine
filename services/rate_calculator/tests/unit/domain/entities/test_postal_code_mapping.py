from rate_calculator.domain.entities import PostalCodeMapping
from rate_calculator.domain.value_objects import District, PostalCode


class TestPostalCodeMapping:
    def test_stores_all_fields(self) -> None:
        mapping = PostalCodeMapping(
            postal_code=PostalCode("80331"),
            district=District("München"),
            region1="Bayern",
            region2="Oberbayern",
            region3="München",
        )
        assert mapping.postal_code == PostalCode("80331")
        assert mapping.district == District("München")
        assert mapping.region1 == "Bayern"
        assert mapping.region2 == "Oberbayern"
        assert mapping.region3 == "München"
