from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, and_, func, desc
from sqlalchemy.orm import sessionmaker
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
from datetime import datetime
import logging
import asyncio

from models import Base, Sneaker, SneakerImage, PriceHistory, ScrapingLog
from config import Config
from scraper_manager import ScraperManager

# Import the enhanced scraper
from enhanced_scraper import EnhancedSneakerScraper

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database setup
engine = create_engine(Config.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)

# FastAPI app
app = FastAPI(
    title="SoleID Sneaker API",
    description="API for sneaker identification and price tracking",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Pydantic models
class SneakerResponse(BaseModel):
    id: int
    name: str
    brand: str
    model: str
    colorway: Optional[str]
    sku: Optional[str]
    retail_price: Optional[float]
    current_price: Optional[float]
    image_url: Optional[str]
    
    class Config:
        from_attributes = True

class SearchRequest(BaseModel):
    query: str
    brand: Optional[str] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None

class ScrapeRequest(BaseModel):
    search_terms: List[str]
    platforms: Optional[List[str]] = ["stockx", "ebay"]

class DatabaseBuildRequest(BaseModel):
    max_per_sneaker: Optional[int] = 30
    custom_sneakers: Optional[List[str]] = None

class DatabaseBuildStatus(BaseModel):
    status: str
    progress: Optional[str] = None
    total_items: Optional[int] = None
    total_images: Optional[int] = None
    error: Optional[str] = None

# Global variable to track database building status
database_build_status = {
    "status": "idle",
    "progress": None,
    "total_items": 0,
    "total_images": 0,
    "error": None
}

# Initialize scraper manager
scraper_manager = ScraperManager()

@app.get("/")
async def root():
    return {"message": "Sneaker Data API", "version": "1.0.0"}

@app.get("/api/sneakers", response_model=List[SneakerResponse])
async def get_sneakers(
    skip: int = 0,
    limit: int = 100,
    brand: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get all sneakers with optional filtering"""
    query = db.query(Sneaker)
    
    if brand:
        query = query.filter(Sneaker.brand.ilike(f"%{brand}%"))
    
    sneakers = query.offset(skip).limit(limit).all()
    
    # Format response with images and current prices
    result = []
    for sneaker in sneakers:
        sneaker_dict = {
            "id": sneaker.id,
            "name": sneaker.name,
            "brand": sneaker.brand,
            "model": sneaker.model,
            "colorway": sneaker.colorway,
            "sku": sneaker.sku,
            "retail_price": sneaker.retail_price,
            "release_date": sneaker.release_date,
            "description": sneaker.description,
            "images": [
                {
                    "url": img.image_url,
                    "type": img.image_type,
                    "is_primary": img.is_primary
                }
                for img in sneaker.images
            ],
            "current_prices": [
                {
                    "size": price.size,
                    "price": price.price,
                    "condition": price.condition,
                    "platform": price.platform,
                    "listing_type": price.listing_type
                }
                for price in sneaker.prices
                if price.listing_type == "current"
            ]
        }
        result.append(sneaker_dict)
    
    return result

@app.get("/api/sneakers/{sneaker_id}", response_model=SneakerResponse)
async def get_sneaker(sneaker_id: int, db: Session = Depends(get_db)):
    """Get specific sneaker by ID"""
    sneaker = db.query(Sneaker).filter(Sneaker.id == sneaker_id).first()
    
    if not sneaker:
        raise HTTPException(status_code=404, detail="Sneaker not found")
    
    return {
        "id": sneaker.id,
        "name": sneaker.name,
        "brand": sneaker.brand,
        "model": sneaker.model,
        "colorway": sneaker.colorway,
        "sku": sneaker.sku,
        "retail_price": sneaker.retail_price,
        "release_date": sneaker.release_date,
        "description": sneaker.description,
        "images": [
            {
                "url": img.image_url,
                "type": img.image_type,
                "is_primary": img.is_primary,
                "google_drive_id": img.google_drive_id
            }
            for img in sneaker.images
        ],
        "current_prices": [
            {
                "size": price.size,
                "price": price.price,
                "condition": price.condition,
                "platform": price.platform,
                "listing_type": price.listing_type,
                "sale_date": price.sale_date
            }
            for price in sneaker.prices
        ]
    }

@app.post("/api/search")
async def search_sneakers(request: SearchRequest, db: Session = Depends(get_db)):
    """Search sneakers with filters"""
    query = db.query(Sneaker)
    
    # Text search
    if request.query:
        query = query.filter(
            Sneaker.name.ilike(f"%{request.query}%") |
            Sneaker.model.ilike(f"%{request.query}%") |
            Sneaker.colorway.ilike(f"%{request.query}%")
        )
    
    # Brand filter
    if request.brand:
        query = query.filter(Sneaker.brand.ilike(f"%{request.brand}%"))
    
    # Price filters (based on current market prices)
    if request.min_price or request.max_price:
        price_subquery = db.query(PriceHistory.sneaker_id).filter(
            PriceHistory.listing_type == "current"
        )
        
        if request.min_price:
            price_subquery = price_subquery.filter(PriceHistory.price >= request.min_price)
        
        if request.max_price:
            price_subquery = price_subquery.filter(PriceHistory.price <= request.max_price)
        
        query = query.filter(Sneaker.id.in_(price_subquery))
    
    sneakers = query.limit(50).all()
    
    return [
        {
            "id": sneaker.id,
            "name": sneaker.name,
            "brand": sneaker.brand,
            "model": sneaker.model,
            "images": [img.image_url for img in sneaker.images if img.is_primary][:1],
            "current_price": min([p.price for p in sneaker.prices if p.listing_type == "current"], default=None)
        }
        for sneaker in sneakers
    ]

@app.post("/api/scrape")
async def trigger_scrape(
    request: ScrapeRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Trigger manual scraping"""
    background_tasks.add_task(
        scraper_manager.scrape_all_platforms,
        request.search_terms,
        request.platforms
    )
    
    return {
        "message": "Scraping started",
        "search_terms": request.search_terms,
        "platforms": request.platforms
    }

@app.post("/api/build-database", response_model=dict)
async def build_database(
    request: DatabaseBuildRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Start building the sneaker database with images and price data"""
    global database_build_status
    
    if database_build_status["status"] == "running":
        raise HTTPException(status_code=400, detail="Database building is already in progress")
    
    # Reset status
    database_build_status = {
        "status": "running",
        "progress": "Starting database build...",
        "total_items": 0,
        "total_images": 0,
        "error": None
    }
    
    # Start background task
    background_tasks.add_task(
        run_database_build,
        request.max_per_sneaker,
        request.custom_sneakers
    )
    
    return {
        "message": "Database building started",
        "status": "running",
        "estimated_time": "30-60 minutes"
    }

@app.get("/api/build-status", response_model=DatabaseBuildStatus)
async def get_build_status():
    """Get the current status of database building"""
    return DatabaseBuildStatus(**database_build_status)

@app.get("/api/database-stats")
async def get_database_stats(db: Session = Depends(get_db)):
    """Get current database statistics"""
    try:
        total_sneakers = db.query(Sneaker).count()
        total_images = db.query(SneakerImage).count()
        total_prices = db.query(PriceHistory).count()
        
        # Get brand distribution
        brand_stats = db.query(
            Sneaker.brand,
            func.count(Sneaker.id).label('count')
        ).group_by(Sneaker.brand).all()
        
        # Get recent scraping logs
        recent_logs = db.query(ScrapingLog).order_by(
            desc(ScrapingLog.created_at)
        ).limit(5).all()
        
        return {
            "total_sneakers": total_sneakers,
            "total_images": total_images,
            "total_prices": total_prices,
            "brand_distribution": [{"brand": brand, "count": count} for brand, count in brand_stats],
            "recent_scraping_logs": [
                {
                    "platform": log.platform,
                    "status": log.status,
                    "items_scraped": log.items_scraped,
                    "created_at": log.created_at
                } for log in recent_logs
            ]
        }
    except Exception as e:
        logger.error(f"Error getting database stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Error retrieving database statistics")

async def run_database_build(max_per_sneaker: int, custom_sneakers: Optional[List[str]]):
    """Background task to run database building"""
    global database_build_status
    
    try:
        database_build_status["progress"] = "Initializing scraper..."
        
        # Create enhanced scraper
        scraper = EnhancedSneakerScraper()
        
        # Get sneaker list
        if custom_sneakers:
            sneaker_list = custom_sneakers
        else:
            sneaker_list = scraper.get_popular_sneakers()
        
        database_build_status["progress"] = f"Starting to scrape {len(sneaker_list)} sneaker models..."
        
        # Build database
        results = scraper.build_sneaker_database(sneaker_list, max_per_sneaker)
        
        # Update status
        database_build_status.update({
            "status": "completed",
            "progress": "Database building completed successfully!",
            "total_items": results["total_items"],
            "total_images": results["total_images"],
            "error": None
        })
        
        logger.info(f"Database build completed: {results}")
        
    except Exception as e:
        logger.error(f"Error in database building: {str(e)}")
        database_build_status.update({
            "status": "error",
            "progress": None,
            "error": str(e)
        })

@app.get("/api/stats")
async def get_stats(db: Session = Depends(get_db)):
    """Get database statistics"""
    total_sneakers = db.query(Sneaker).count()
    total_images = db.query(SneakerImage).count()
    total_prices = db.query(PriceHistory).count()
    
    brands = db.query(Sneaker.brand).distinct().all()
    brand_counts = {}
    for brand in brands:
        brand_counts[brand[0]] = db.query(Sneaker).filter(Sneaker.brand == brand[0]).count()
    
    return {
        "total_sneakers": total_sneakers,
        "total_images": total_images,
        "total_prices": total_prices,
        "brands": brand_counts
    }

if __name__ == "__main__":
    uvicorn.run(
        "api:app",
        host=Config.API_HOST,
        port=Config.API_PORT,
        reload=True
    )