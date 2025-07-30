from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import ForeignKey
from datetime import datetime

Base = declarative_base()

class Sneaker(Base):
    __tablename__ = "sneakers"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    brand = Column(String, nullable=False, index=True)
    model = Column(String, nullable=False)
    colorway = Column(String)
    sku = Column(String, unique=True, index=True)
    retail_price = Column(Float)
    release_date = Column(DateTime)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    images = relationship("SneakerImage", back_populates="sneaker")
    prices = relationship("PriceHistory", back_populates="sneaker")

class SneakerImage(Base):
    __tablename__ = "sneaker_images"
    
    id = Column(Integer, primary_key=True, index=True)
    sneaker_id = Column(Integer, ForeignKey("sneakers.id"))
    image_url = Column(String, nullable=False)
    google_drive_id = Column(String)
    image_type = Column(String)  # main, side, back, detail, etc.
    is_primary = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    sneaker = relationship("Sneaker", back_populates="images")

class PriceHistory(Base):
    __tablename__ = "price_history"
    
    id = Column(Integer, primary_key=True, index=True)
    sneaker_id = Column(Integer, ForeignKey("sneakers.id"))
    size = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    condition = Column(String)  # new, used, etc.
    platform = Column(String, nullable=False)  # stockx, goat, ebay, etc.
    sale_date = Column(DateTime)
    listing_type = Column(String)  # sold, current, bid, etc.
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    sneaker = relationship("Sneaker", back_populates="prices")

class ScrapingLog(Base):
    __tablename__ = "scraping_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    platform = Column(String, nullable=False)
    status = Column(String, nullable=False)  # success, error, partial
    items_scraped = Column(Integer, default=0)
    errors_count = Column(Integer, default=0)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime)
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)