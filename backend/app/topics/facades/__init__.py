from app.topics.facades.arxiv import ArxivFacade
from app.topics.facades.mlb import MLBFacade
from app.topics.facades.rss import RSSFacade

FACADE_REGISTRY = {
    "rss": RSSFacade,
    "arxiv": ArxivFacade,
    "mlb": MLBFacade,
}
