from dataclasses import dataclass


@dataclass
class Product:
    name: str
    price: str
    rating: float | None
    review_count: int
    url: str
    image_url: str | None = None
    badge: str | None = None
    kpi_score: float | None = None
