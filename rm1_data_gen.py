#!/usr/bin/env python3
"""
Real Estate Data Generator for Revenue Management System
Generates synthetic sales and listings data with configurable parameters

Copyright (c) 2026 Sasha Gutfraind
Repository: https://github.com/sashagutfraind/homeseller_ai_agent

This software is provided as-is for educational and research purposes.
See LICENSE.md for full license details.
"""

import json
import random
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import List, Dict, Literal
from enum import Enum


# ============================================================================
# CONFIGURATION CLASSES
# ============================================================================

@dataclass
class TimeWindowConfig:
    """Controls the time period for data generation"""
    start_date: str = "2024-01-01"  # YYYY-MM-DD
    end_date: str = "2026-03-22"
    listing_creation_rate_per_month: int = 50  # New listings per month
    

@dataclass
class PropertyStockConfig:
    """Defines the composition of local property inventory"""
    # Property type distribution (must sum to 1.0)
    single_family_pct: float = 0.60
    condo_pct: float = 0.25
    townhouse_pct: float = 0.15
    
    # Size distribution (sqft ranges and probabilities)
    size_small_pct: float = 0.30  # 800-1500 sqft
    size_medium_pct: float = 0.50  # 1500-3000 sqft
    size_large_pct: float = 0.20  # 3000-6000 sqft
    
    # Age distribution
    new_construction_pct: float = 0.10  # < 5 years
    modern_pct: float = 0.30  # 5-20 years
    established_pct: float = 0.40  # 20-50 years
    vintage_pct: float = 0.20  # > 50 years
    
    # Condition distribution
    excellent_condition_pct: float = 0.15  # A, A-
    good_condition_pct: float = 0.50  # B+, B
    fair_condition_pct: float = 0.30  # C+, C
    poor_condition_pct: float = 0.05  # D


@dataclass
class EconomicTrendsConfig:
    """Models economic factors affecting the market"""
    # Mortgage rates over time
    initial_mortgage_rate: float = 6.8
    final_mortgage_rate: float = 6.1
    rate_volatility: float = 0.3  # Random fluctuation
    
    # Market velocity (how fast properties sell)
    market_velocity: Literal["HOT", "WARM", "COOLING", "COLD"] = "WARM"
    velocity_trend: Literal["INCREASING", "STABLE", "DECREASING"] = "STABLE"
    
    # Price appreciation (annual %)
    annual_appreciation_rate: float = 3.5
    appreciation_volatility: float = 2.0
    
    # Inventory levels
    months_of_inventory: float = 4.5  # Balanced market ~6 months
    inventory_trend: Literal["INCREASING", "STABLE", "DECREASING"] = "STABLE"


@dataclass
class PricingBehaviorConfig:
    """Controls pricing strategies and outcomes"""
    # Initial pricing strategy distribution
    priced_at_market_pct: float = 0.60
    priced_above_market_pct: float = 0.25
    priced_below_market_pct: float = 0.15
    
    # Pricing aggressiveness
    above_market_premium_mean: float = 8.0  # % above market
    above_market_premium_std: float = 5.0
    below_market_discount_mean: float = 5.0  # % below market
    below_market_discount_std: float = 3.0
    
    # Sale outcomes
    avg_sale_to_list_ratio: float = 0.98
    sale_to_list_std: float = 0.05
    
    # Price reductions
    price_reduction_probability: float = 0.35
    avg_price_reduction_pct: float = 5.0


@dataclass
class MarketDynamicsConfig:
    """Controls market behavior and competition"""
    # Days on market
    avg_days_on_market: int = 45
    dom_std: int = 30
    
    # Multiple offers
    multiple_offer_probability: float = 0.25
    avg_competing_offers: int = 4
    
    # Seller concessions
    concessions_probability: float = 0.40
    avg_concessions_amount: int = 4000
    
    # Seasonal factors
    spring_boost: float = 1.15  # Multiplier for spring market
    summer_boost: float = 1.10
    fall_boost: float = 0.95
    winter_boost: float = 0.85


@dataclass
class GeographicConfig:
    """Defines geographic parameters"""
    city: str = "Chicago"
    state: str = "IL"
    zip_codes: List[str] = None
    
    # Price ranges by zip (median prices)
    zip_price_medians: Dict[str, int] = None
    
    def __post_init__(self):
        if self.zip_codes is None:
            self.zip_codes = ["60614", "60657", "60610", "60611", "60622"]
        if self.zip_price_medians is None:
            self.zip_price_medians = {
                "60614": 650000,
                "60657": 620000,
                "60610": 580000,
                "60611": 720000,
                "60622": 550000
            }


@dataclass
class DataGenerationConfig:
    """Master configuration for data generation"""
    time_window: TimeWindowConfig
    property_stock: PropertyStockConfig
    economic_trends: EconomicTrendsConfig
    pricing_behavior: PricingBehaviorConfig
    market_dynamics: MarketDynamicsConfig
    geographic: GeographicConfig
    
    # Output settings
    num_sales: int = 200
    num_active_listings: int = 75
    random_seed: int = 42


# ============================================================================
# DATA GENERATOR
# ============================================================================

class RealEstateDataGenerator:
    """Generates synthetic real estate sales and listings data"""
    
    def __init__(self, config: DataGenerationConfig):
        self.config = config
        random.seed(config.random_seed)
        self.property_counter = 10000
        
    def generate_property_id(self) -> str:
        """Generate unique property ID"""
        self.property_counter += 1
        prefix = random.choice(["ATTOM", "RE", "MLS"])
        return f"{prefix}-{self.property_counter}-{self.config.geographic.state}"
    
    def generate_address(self, zip_code: str) -> str:
        """Generate realistic address"""
        street_num = random.randint(100, 9999)
        streets = ["Oak St", "Maple Ave", "State St", "Clark St", "Halsted St", 
                   "Ashland Ave", "Lincoln Ave", "Diversey Pkwy", "Fullerton Ave"]
        street = random.choice(streets)
        return f"{street_num} {street}, {self.config.geographic.city}, {self.config.geographic.state} {zip_code}"
    
    def get_seasonal_multiplier(self, date: datetime) -> float:
        """Get seasonal price multiplier"""
        month = date.month
        if month in [3, 4, 5]:
            return self.config.market_dynamics.spring_boost
        elif month in [6, 7, 8]:
            return self.config.market_dynamics.summer_boost
        elif month in [9, 10, 11]:
            return self.config.market_dynamics.fall_boost
        else:
            return self.config.market_dynamics.winter_boost
    
    def generate_property_features(self) -> Dict:
        """Generate property characteristics"""
        # Determine property type
        rand = random.random()
        if rand < self.config.property_stock.single_family_pct:
            prop_type = "single_family"
        elif rand < self.config.property_stock.single_family_pct + self.config.property_stock.condo_pct:
            prop_type = "condo"
        else:
            prop_type = "townhouse"
        
        # Determine size
        rand = random.random()
        if rand < self.config.property_stock.size_small_pct:
            sqft = random.randint(800, 1500)
            beds = random.randint(1, 2)
            baths = random.randint(1, 2)
        elif rand < self.config.property_stock.size_small_pct + self.config.property_stock.size_medium_pct:
            sqft = random.randint(1500, 3000)
            beds = random.randint(2, 4)
            baths = random.randint(2, 3)
        else:
            sqft = random.randint(3000, 6000)
            beds = random.randint(4, 6)
            baths = random.randint(3, 5)
        
        # Determine age
        current_year = 2026
        rand = random.random()
        if rand < self.config.property_stock.new_construction_pct:
            year_built = random.randint(current_year - 5, current_year)
        elif rand < self.config.property_stock.new_construction_pct + self.config.property_stock.modern_pct:
            year_built = random.randint(current_year - 20, current_year - 5)
        elif rand < (self.config.property_stock.new_construction_pct + 
                     self.config.property_stock.modern_pct + 
                     self.config.property_stock.established_pct):
            year_built = random.randint(current_year - 50, current_year - 20)
        else:
            year_built = random.randint(1900, current_year - 50)
        
        # Determine condition
        rand = random.random()
        if rand < self.config.property_stock.excellent_condition_pct:
            condition = random.choice(["A", "A-"])
        elif rand < (self.config.property_stock.excellent_condition_pct + 
                     self.config.property_stock.good_condition_pct):
            condition = random.choice(["B+", "B"])
        elif rand < (self.config.property_stock.excellent_condition_pct + 
                     self.config.property_stock.good_condition_pct +
                     self.config.property_stock.fair_condition_pct):
            condition = random.choice(["C+", "C"])
        else:
            condition = "D"
        
        features = {
            "beds": beds,
            "baths": baths,
            "sqft": sqft,
            "lot_size_ac": round(random.uniform(0.05, 0.5), 2) if prop_type != "condo" else None,
            "condition_grade": condition,
            "year_built": year_built
        }
        
        # Add renovation for older properties
        if year_built < current_year - 10 and random.random() < 0.3:
            features["last_reno_year"] = random.randint(max(year_built + 5, current_year - 10), current_year)
        
        return features
    
    def calculate_base_price(self, features: Dict, zip_code: str) -> int:
        """Calculate base property price"""
        median = self.config.geographic.zip_price_medians[zip_code]
        
        # Price per sqft based on median
        base_ppsf = median / 2000  # Assume median is for 2000 sqft
        
        # Adjust for condition
        condition_multipliers = {
            "A": 1.15, "A-": 1.10, "B+": 1.05, "B": 1.0,
            "C+": 0.95, "C": 0.90, "D": 0.80
        }
        condition_mult = condition_multipliers.get(features["condition_grade"], 1.0)
        
        # Adjust for age
        age = 2026 - features["year_built"]
        if age < 5:
            age_mult = 1.10
        elif age < 20:
            age_mult = 1.0
        elif age < 50:
            age_mult = 0.95
        else:
            age_mult = 0.90
        
        # Recent renovation boost
        if "last_reno_year" in features and features["last_reno_year"] > 2020:
            age_mult *= 1.08
        
        price = base_ppsf * features["sqft"] * condition_mult * age_mult
        return int(price)
    
    def generate_sale(self) -> Dict:
        """Generate a completed sale record"""
        # Generate sale date
        start = datetime.strptime(self.config.time_window.start_date, "%Y-%m-%d")
        end = datetime.strptime(self.config.time_window.end_date, "%Y-%m-%d")
        days_range = (end - start).days
        sale_date = start + timedelta(days=random.randint(0, days_range))
        
        # Select zip code
        zip_code = random.choice(self.config.geographic.zip_codes)
        
        # Generate property features
        features = self.generate_property_features()
        
        # Calculate base price
        base_price = self.calculate_base_price(features, zip_code)
        
        # Apply economic trends
        days_since_start = (sale_date - start).days
        years_elapsed = days_since_start / 365.25
        appreciation = (1 + self.config.economic_trends.annual_appreciation_rate / 100) ** years_elapsed
        appreciation *= random.gauss(1.0, self.config.economic_trends.appreciation_volatility / 100)
        
        # Apply seasonal factors
        seasonal_mult = self.get_seasonal_multiplier(sale_date)
        
        market_price = int(base_price * appreciation * seasonal_mult)
        
        # Determine listing strategy
        rand = random.random()
        if rand < self.config.pricing_behavior.priced_at_market_pct:
            list_price = market_price
        elif rand < (self.config.pricing_behavior.priced_at_market_pct + 
                     self.config.pricing_behavior.priced_above_market_pct):
            premium = random.gauss(
                self.config.pricing_behavior.above_market_premium_mean,
                self.config.pricing_behavior.above_market_premium_std
            )
            list_price = int(market_price * (1 + premium / 100))
        else:
            discount = random.gauss(
                self.config.pricing_behavior.below_market_discount_mean,
                self.config.pricing_behavior.below_market_discount_std
            )
            list_price = int(market_price * (1 - discount / 100))
        
        # Calculate sold price
        sale_to_list = random.gauss(
            self.config.pricing_behavior.avg_sale_to_list_ratio,
            self.config.pricing_behavior.sale_to_list_std
        )
        sold_price = int(list_price * sale_to_list)
        
        # Days on market
        dom = max(1, int(random.gauss(
            self.config.market_dynamics.avg_days_on_market,
            self.config.market_dynamics.dom_std
        )))
        
        # Build sale details
        sale_details = {
            "sold_price": sold_price,
            "sold_date": sale_date.strftime("%Y-%m-%d"),
            "original_list_price": list_price,
            "sale_to_list_ratio": round(sold_price / list_price, 3),
            "days_on_market": dom
        }
        
        # Add optional fields
        if random.random() < self.config.market_dynamics.multiple_offer_probability:
            sale_details["competing_offers"] = random.randint(2, self.config.market_dynamics.avg_competing_offers + 3)
        
        if random.random() < self.config.market_dynamics.concessions_probability:
            sale_details["concessions_paid"] = random.randint(
                2000, self.config.market_dynamics.avg_concessions_amount + 3000
            )
        
        # Market context
        mortgage_rate = self.config.economic_trends.initial_mortgage_rate + (
            (self.config.economic_trends.final_mortgage_rate - 
             self.config.economic_trends.initial_mortgage_rate) * 
            (days_since_start / days_range)
        )
        mortgage_rate += random.gauss(0, self.config.economic_trends.rate_volatility)
        
        market_context = {
            "zip_median_sale": self.config.geographic.zip_price_medians[zip_code],
            "neighborhood_velocity": self.config.economic_trends.velocity_trend,
            "mortgage_rate_at_sale": round(mortgage_rate, 2)
        }
        
        return {
            "property_id": self.generate_property_id(),
            "address": self.generate_address(zip_code),
            "status": "SOLD",
            "sale_details": sale_details,
            "features": features,
            "market_context": market_context
        }
    
    def generate_listing(self) -> Dict:
        """Generate an active listing record"""
        # Similar to sale but status is ACTIVE
        sale = self.generate_sale()
        
        # Convert to active listing
        listing_date = datetime.strptime(sale["sale_details"]["sold_date"], "%Y-%m-%d")
        days_on_market = random.randint(1, 90)
        
        listing = {
            "property_id": sale["property_id"],
            "address": sale["address"],
            "status": "ACTIVE",
            "listing_details": {
                "list_price": sale["sale_details"]["original_list_price"],
                "list_date": (listing_date - timedelta(days=days_on_market)).strftime("%Y-%m-%d"),
                "days_on_market": days_on_market,
                "views": random.randint(50, 500),
                "showings": random.randint(2, 20)
            },
            "features": sale["features"],
            "market_context": sale["market_context"]
        }
        
        # Add price history if reduced
        if random.random() < self.config.pricing_behavior.price_reduction_probability:
            original_price = int(listing["listing_details"]["list_price"] * 
                               (1 + self.config.pricing_behavior.avg_price_reduction_pct / 100))
            listing["listing_details"]["original_list_price"] = original_price
            listing["listing_details"]["price_reductions"] = 1
        
        return listing
    
    def generate_dataset(self) -> tuple[List[Dict], List[Dict]]:
        """Generate complete dataset of sales and listings"""
        print(f"Generating {self.config.num_sales} sales...")
        sales = [self.generate_sale() for _ in range(self.config.num_sales)]
        
        print(f"Generating {self.config.num_active_listings} active listings...")
        listings = [self.generate_listing() for _ in range(self.config.num_active_listings)]
        
        return sales, listings


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def create_default_config() -> DataGenerationConfig:
    """Create default configuration"""
    return DataGenerationConfig(
        time_window=TimeWindowConfig(),
        property_stock=PropertyStockConfig(),
        economic_trends=EconomicTrendsConfig(),
        pricing_behavior=PricingBehaviorConfig(),
        market_dynamics=MarketDynamicsConfig(),
        geographic=GeographicConfig(),
        num_sales=200,
        num_active_listings=75,
        random_seed=42
    )


def main():
    """Main execution function"""
    print("=" * 70)
    print("Real Estate Data Generator")
    print("=" * 70)
    
    # Create configuration
    config = create_default_config()
    
    # Initialize generator
    generator = RealEstateDataGenerator(config)
    
    # Generate data
    sales, listings = generator.generate_dataset()
    
    # Save to files
    sales_file = "data-generated/ATTOM-sales.json"
    listings_file = "data-generated/ATTOM-listings.json"
    
    with open(sales_file, 'w') as f:
        json.dump(sales, f, indent=2)
    print(f"\n✓ Saved {len(sales)} sales to {sales_file}")
    
    with open(listings_file, 'w') as f:
        json.dump(listings, f, indent=2)
    print(f"✓ Saved {len(listings)} listings to {listings_file}")
    
    # Print summary statistics
    print("\n" + "=" * 70)
    print("GENERATION SUMMARY")
    print("=" * 70)
    print(f"Time Window: {config.time_window.start_date} to {config.time_window.end_date}")
    print(f"Geographic: {config.geographic.city}, {config.geographic.state}")
    print(f"Zip Codes: {', '.join(config.geographic.zip_codes)}")
    print(f"Market Velocity: {config.economic_trends.market_velocity}")
    print(f"Avg Days on Market: {config.market_dynamics.avg_days_on_market}")
    print(f"Annual Appreciation: {config.economic_trends.annual_appreciation_rate}%")
    
    avg_sale_price = sum(s["sale_details"]["sold_price"] for s in sales) / len(sales)
    print(f"\nAverage Sale Price: ${avg_sale_price:,.0f}")
    
    avg_list_price = sum(l["listing_details"]["list_price"] for l in listings) / len(listings)
    print(f"Average List Price: ${avg_list_price:,.0f}")
    
    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
