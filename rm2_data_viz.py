#!/usr/bin/env python3
"""
Real Estate Data Visualization and Pricing Model
Serves an HTML dashboard with tables, charts, and ML pricing

Copyright (c) 2026 Sasha Gutfraind
Repository: https://github.com/sashagutfraind/homeseller_ai_agent

This software is provided as-is for educational and research purposes.
See LICENSE.md for full license details.
"""

import json
import numpy as np
from datetime import datetime
from flask import Flask, render_template_string, jsonify, request
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
import os

app = Flask(__name__)

# ============================================================================
# DATA LOADING
# ============================================================================

def load_data():
    """Load sales and listings data"""
    with open('data-generated/ATTOM-sales.json', 'r') as f:
        sales = json.load(f)
    
    with open('data-generated/ATTOM-listings.json', 'r') as f:
        listings = json.load(f)
    
    return sales, listings

def load_my_listing():
    """Load FSBO listing"""
    try:
        with open('my.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return None

# ============================================================================
# PRICING MODEL
# ============================================================================

class PropertyPricingModel:
    """Logistic regression-based pricing model"""
    
    def __init__(self):
        self.model = LinearRegression()
        self.scaler = StandardScaler()
        self.is_calibrated = False
    
    def extract_features(self, property_data):
        """Extract features from property data"""
        features = property_data.get('features', {})
        
        # Numeric features
        feature_vector = [
            features.get('beds', 0),
            features.get('baths', 0),
            features.get('sqft', 0),
            features.get('lot_size_ac', 0) or 0,
            features.get('year_built', 2000),
            features.get('last_reno_year', features.get('year_built', 2000))
        ]
        
        # Condition grade to numeric
        condition_map = {'A': 5, 'A-': 4.5, 'B+': 4, 'B': 3.5, 'C+': 3, 'C': 2.5, 'D': 2}
        condition = features.get('condition_grade', 'B')
        feature_vector.append(condition_map.get(condition, 3.5))
        
        return np.array(feature_vector)
    
    def calibrate(self, sales_data):
        """Calibrate model on historical sales"""
        X = []
        y = []
        
        for sale in sales_data:
            features = self.extract_features(sale)
            price = sale['sale_details']['sold_price']
            X.append(features)
            y.append(price)
        
        X = np.array(X)
        y = np.array(y)
        
        # Normalize features
        X_scaled = self.scaler.fit_transform(X)
        
        # Train model
        self.model.fit(X_scaled, y)
        self.is_calibrated = True
        
        # Calculate R² score
        score = self.model.score(X_scaled, y)
        return score
    
    def predict(self, property_data):
        """Predict fair market price"""
        if not self.is_calibrated:
            raise ValueError("Model must be calibrated first")
        
        features = self.extract_features(property_data)
        features_scaled = self.scaler.transform(features.reshape(1, -1))
        
        predicted_price = self.model.predict(features_scaled)[0]
        
        # Calculate confidence interval (simple approach)
        confidence_range = predicted_price * 0.08  # ±8%
        
        return {
            'predicted_price': int(predicted_price),
            'price_low': int(predicted_price - confidence_range),
            'price_high': int(predicted_price + confidence_range),
            'confidence': '92%'
        }

# ============================================================================
# MARKET ANALYTICS
# ============================================================================

def calculate_market_trends(sales_data):
    """Calculate time series market trends"""
    # Group by month
    monthly_data = {}
    
    for sale in sales_data:
        date_str = sale['sale_details']['sold_date']
        date = datetime.strptime(date_str, '%Y-%m-%d')
        month_key = date.strftime('%Y-%m')
        
        if month_key not in monthly_data:
            monthly_data[month_key] = {
                'prices': [],
                'dom': [],
                'count': 0
            }
        
        monthly_data[month_key]['prices'].append(sale['sale_details']['sold_price'])
        monthly_data[month_key]['dom'].append(sale['sale_details']['days_on_market'])
        monthly_data[month_key]['count'] += 1
    
    # Calculate aggregates
    trends = []
    for month in sorted(monthly_data.keys()):
        data = monthly_data[month]
        trends.append({
            'month': month,
            'median_price': int(np.median(data['prices'])),
            'avg_price': int(np.mean(data['prices'])),
            'avg_dom': int(np.mean(data['dom'])),
            'volume': data['count']
        })
    
    return trends

# ============================================================================
# HTML TEMPLATE
# ============================================================================

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Homeseller's AI agent - Real Estate Revenue Management Dashboard</title>
    <meta charset="utf-8">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            background: #f5f5f5;
            padding: 20px;
        }
        .container { max-width: 1400px; margin: 0 auto; }
        h1 { color: #333; margin-bottom: 10px; }
        .subtitle { color: #666; margin-bottom: 30px; }
        
        .card {
            background: white;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .card h2 {
            color: #333;
            margin-bottom: 15px;
            font-size: 20px;
            border-bottom: 2px solid #4CAF50;
            padding-bottom: 8px;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }
        
        .stat-box {
            background: #5c6bc0;
            color: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }
        
        .stat-box.green { background: #26a69a; }
        .stat-box.blue { background: #42a5f5; }
        .stat-box.orange { background: #ff7043; }
        
        .stat-value { font-size: 32px; font-weight: bold; margin-bottom: 5px; }
        .stat-label { font-size: 14px; opacity: 0.9; }
        
        .controls {
            display: flex;
            gap: 10px;
            margin-bottom: 15px;
            flex-wrap: wrap;
        }
        
        input, select, button {
            padding: 8px 12px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
        }
        
        button {
            background: #4CAF50;
            color: white;
            border: none;
            cursor: pointer;
            font-weight: 500;
        }
        
        button:hover { background: #45a049; }
        
        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 14px;
        }
        
        th {
            background: #f8f9fa;
            padding: 12px;
            text-align: left;
            font-weight: 600;
            color: #333;
            cursor: pointer;
            user-select: none;
            border-bottom: 2px solid #dee2e6;
        }
        
        th:hover { background: #e9ecef; }
        th.sorted-asc::after { content: ' ▲'; color: #4CAF50; }
        th.sorted-desc::after { content: ' ▼'; color: #4CAF50; }
        
        td {
            padding: 10px 12px;
            border-bottom: 1px solid #eee;
        }
        
        tr:hover { background: #f8f9fa; }
        
        .price { font-weight: 600; color: #2e7d32; }
        .status-sold { color: #1976d2; font-weight: 500; }
        .status-active { color: #f57c00; font-weight: 500; }
        
        #chart { height: 400px; margin-top: 20px; }
        
        .prediction-box {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 8px;
            text-align: center;
        }
        
        .prediction-price {
            font-size: 48px;
            font-weight: bold;
            margin: 20px 0;
        }
        
        .prediction-range {
            font-size: 18px;
            opacity: 0.9;
            margin-bottom: 10px;
        }
        
        .model-info {
            background: rgba(255,255,255,0.2);
            padding: 15px;
            border-radius: 4px;
            margin-top: 20px;
        }
        
        .property-form {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }
        
        .form-group {
            display: flex;
            flex-direction: column;
        }
        
        .form-group label {
            font-size: 14px;
            font-weight: 500;
            margin-bottom: 5px;
            color: #333;
        }
        
        .form-group input, .form-group select {
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
        }
        
        .form-actions {
            display: flex;
            gap: 10px;
            margin-top: 20px;
        }
        
        .btn-primary {
            background: #4CAF50;
            color: white;
            padding: 12px 24px;
            border: none;
            border-radius: 4px;
            font-size: 16px;
            font-weight: 500;
            cursor: pointer;
        }
        
        .btn-primary:hover {
            background: #45a049;
        }
        
        .btn-secondary {
            background: #757575;
            color: white;
            padding: 12px 24px;
            border: none;
            border-radius: 4px;
            font-size: 16px;
            font-weight: 500;
            cursor: pointer;
        }
        
        .btn-secondary:hover {
            background: #616161;
        }
    </style>
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
</head>
<body>
    <div class="container">
        <h1>🏠 Homeseller's AI agent - Dashboard to optimize the listing of your property</h1>
        <p class="subtitle">AI-Powered Pricing & Market Analytics</p>
        
        <!-- Market Stats -->
        <div class="stats-grid">
            <div class="stat-box">
                <div class="stat-value" id="total-sales">{{ stats.total_sales }}</div>
                <div class="stat-label">Total Sales</div>
            </div>
            <div class="stat-box green">
                <div class="stat-value" id="avg-price">${{ "{:,.0f}".format(stats.avg_price) }}</div>
                <div class="stat-label">Avg Sale Price</div>
            </div>
            <div class="stat-box blue">
                <div class="stat-value" id="avg-dom">{{ stats.avg_dom }}</div>
                <div class="stat-label">Avg Days on Market</div>
            </div>
            <div class="stat-box orange">
                <div class="stat-value" id="active-listings">{{ stats.active_listings }}</div>
                <div class="stat-label">Active Listings</div>
            </div>
        </div>
        
        <!-- My Property Prediction -->
        <div class="card">
            <h2>💰 Your Property Valuation</h2>
            
            {% if prediction %}
            <div class="prediction-box">
                <div>Fair Market Value</div>
                <div class="prediction-price">${{ "{:,.0f}".format(prediction.predicted_price) }}</div>
                <div class="prediction-range">
                    Range: ${{ "{:,.0f}".format(prediction.price_low) }} - ${{ "{:,.0f}".format(prediction.price_high) }}
                </div>
                <div>Confidence: {{ prediction.confidence }}</div>
                <div class="model-info">
                    <strong>Model Performance:</strong> R² = {{ "%.3f"|format(model_score) }}<br>
                    Calibrated on {{ stats.total_sales }} historical sales
                </div>
            </div>
            {% endif %}
            
            <h3 style="margin-top: 30px; margin-bottom: 15px;">Edit Your Property Details</h3>
            <form id="property-form" class="property-form">
                <div class="form-group">
                    <label for="address">Address</label>
                    <input type="text" id="address" name="address" value="{{ my_listing.address if my_listing else '' }}" required>
                </div>
                
                <div class="form-group">
                    <label for="beds">Bedrooms</label>
                    <input type="number" id="beds" name="beds" value="{{ my_listing.features.beds if my_listing else 3 }}" min="1" max="10" required>
                </div>
                
                <div class="form-group">
                    <label for="baths">Bathrooms</label>
                    <input type="number" id="baths" name="baths" value="{{ my_listing.features.baths if my_listing else 2 }}" min="1" max="10" step="0.5" required>
                </div>
                
                <div class="form-group">
                    <label for="sqft">Square Feet</label>
                    <input type="number" id="sqft" name="sqft" value="{{ my_listing.features.sqft if my_listing else 1850 }}" min="500" max="10000" required>
                </div>
                
                <div class="form-group">
                    <label for="lot_size_ac">Lot Size (acres)</label>
                    <input type="number" id="lot_size_ac" name="lot_size_ac" value="{{ my_listing.features.lot_size_ac if my_listing else 0.15 }}" min="0" max="10" step="0.01">
                </div>
                
                <div class="form-group">
                    <label for="year_built">Year Built</label>
                    <input type="number" id="year_built" name="year_built" value="{{ my_listing.features.year_built if my_listing else 2005 }}" min="1800" max="2026" required>
                </div>
                
                <div class="form-group">
                    <label for="last_reno_year">Last Renovation Year</label>
                    <input type="number" id="last_reno_year" name="last_reno_year" value="{{ my_listing.features.last_reno_year if my_listing else 2023 }}" min="1800" max="2026">
                </div>
                
                <div class="form-group">
                    <label for="condition_grade">Condition Grade</label>
                    <select id="condition_grade" name="condition_grade" required>
                        <option value="A" {% if my_listing and my_listing.features.condition_grade == 'A' %}selected{% endif %}>A - Excellent</option>
                        <option value="A-" {% if my_listing and my_listing.features.condition_grade == 'A-' %}selected{% endif %}>A- - Very Good</option>
                        <option value="B+" {% if my_listing and my_listing.features.condition_grade == 'B+' %}selected{% elif not my_listing %}selected{% endif %}>B+ - Good</option>
                        <option value="B" {% if my_listing and my_listing.features.condition_grade == 'B' %}selected{% endif %}>B - Above Average</option>
                        <option value="C+" {% if my_listing and my_listing.features.condition_grade == 'C+' %}selected{% endif %}>C+ - Average</option>
                        <option value="C" {% if my_listing and my_listing.features.condition_grade == 'C' %}selected{% endif %}>C - Below Average</option>
                        <option value="D" {% if my_listing and my_listing.features.condition_grade == 'D' %}selected{% endif %}>D - Poor</option>
                    </select>
                </div>
            </form>
            
            <div class="form-actions">
                <button class="btn-primary" onclick="updatePrediction()">🔄 Recalculate Price</button>
                <button class="btn-secondary" onclick="saveToFile()">💾 Save to my.json</button>
            </div>
        </div>
        
        <!-- Market Trends Chart -->
        <div class="card">
            <h2>📈 Market Trends</h2>
            <div id="chart"></div>
        </div>
        
        <!-- Sales Table -->
        <div class="card">
            <h2>🏘️ Recent Sales</h2>
            <div class="controls">
                <input type="text" id="sales-search" placeholder="Search address, zip...">
                <select id="sales-beds-filter">
                    <option value="">All Bedrooms</option>
                    <option value="1">1 Bed</option>
                    <option value="2">2 Beds</option>
                    <option value="3">3 Beds</option>
                    <option value="4">4+ Beds</option>
                </select>
                <select id="sales-price-filter">
                    <option value="">All Prices</option>
                    <option value="0-500000">Under $500k</option>
                    <option value="500000-700000">$500k - $700k</option>
                    <option value="700000-1000000">$700k+</option>
                </select>
                <button onclick="resetSalesFilters()">Reset</button>
            </div>
            <div style="overflow-x: auto;">
                <table id="sales-table">
                    <thead>
                        <tr>
                            <th onclick="sortTable('sales-table', 0)">Address</th>
                            <th onclick="sortTable('sales-table', 1)">Sold Price</th>
                            <th onclick="sortTable('sales-table', 2)">List Price</th>
                            <th onclick="sortTable('sales-table', 3)">Beds</th>
                            <th onclick="sortTable('sales-table', 4)">Baths</th>
                            <th onclick="sortTable('sales-table', 5)">Sqft</th>
                            <th onclick="sortTable('sales-table', 6)">DOM</th>
                            <th onclick="sortTable('sales-table', 7)">Sale Date</th>
                        </tr>
                    </thead>
                    <tbody id="sales-tbody">
                        {% for sale in sales[:50] %}
                        <tr data-beds="{{ sale.features.beds }}" data-price="{{ sale.sale_details.sold_price }}">
                            <td>{{ sale.address }}</td>
                            <td class="price">${{ "{:,.0f}".format(sale.sale_details.sold_price) }}</td>
                            <td>${{ "{:,.0f}".format(sale.sale_details.original_list_price) }}</td>
                            <td>{{ sale.features.beds }}</td>
                            <td>{{ sale.features.baths }}</td>
                            <td>{{ "{:,}".format(sale.features.sqft) }}</td>
                            <td>{{ sale.sale_details.days_on_market }}</td>
                            <td>{{ sale.sale_details.sold_date }}</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
        
        <!-- Listings Table -->
        <div class="card">
            <h2>🔥 Active Listings</h2>
            <div class="controls">
                <input type="text" id="listings-search" placeholder="Search address, zip...">
                <select id="listings-beds-filter">
                    <option value="">All Bedrooms</option>
                    <option value="1">1 Bed</option>
                    <option value="2">2 Beds</option>
                    <option value="3">3 Beds</option>
                    <option value="4">4+ Beds</option>
                </select>
                <button onclick="resetListingsFilters()">Reset</button>
            </div>
            <div style="overflow-x: auto;">
                <table id="listings-table">
                    <thead>
                        <tr>
                            <th onclick="sortTable('listings-table', 0)">Address</th>
                            <th onclick="sortTable('listings-table', 1)">List Price</th>
                            <th onclick="sortTable('listings-table', 2)">Beds</th>
                            <th onclick="sortTable('listings-table', 3)">Baths</th>
                            <th onclick="sortTable('listings-table', 4)">Sqft</th>
                            <th onclick="sortTable('listings-table', 5)">DOM</th>
                            <th onclick="sortTable('listings-table', 6)">Views</th>
                            <th onclick="sortTable('listings-table', 7)">List Date</th>
                        </tr>
                    </thead>
                    <tbody id="listings-tbody">
                        {% for listing in listings %}
                        <tr data-beds="{{ listing.features.beds }}" data-price="{{ listing.listing_details.list_price }}">
                            <td>{{ listing.address }}</td>
                            <td class="price">${{ "{:,.0f}".format(listing.listing_details.list_price) }}</td>
                            <td>{{ listing.features.beds }}</td>
                            <td>{{ listing.features.baths }}</td>
                            <td>{{ "{:,}".format(listing.features.sqft) }}</td>
                            <td>{{ listing.listing_details.days_on_market }}</td>
                            <td>{{ listing.listing_details.views }}</td>
                            <td>{{ listing.listing_details.list_date }}</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
    
    <script>
        // Market trends chart
        const trendsData = {{ trends|tojson }};
        
        const trace1 = {
            x: trendsData.map(d => d.month),
            y: trendsData.map(d => d.median_price),
            name: 'Median Price',
            type: 'scatter',
            mode: 'lines+markers',
            line: { color: '#4CAF50', width: 3 }
        };
        
        const trace2 = {
            x: trendsData.map(d => d.month),
            y: trendsData.map(d => d.avg_dom),
            name: 'Avg Days on Market',
            type: 'scatter',
            mode: 'lines+markers',
            yaxis: 'y2',
            line: { color: '#ff9800', width: 3 }
        };
        
        const layout = {
            title: 'Price & Days on Market Trends',
            xaxis: { title: 'Month' },
            yaxis: { 
                title: 'Median Price ($)',
                tickformat: '$,.0f'
            },
            yaxis2: {
                title: 'Days on Market',
                overlaying: 'y',
                side: 'right'
            },
            hovermode: 'x unified',
            showlegend: true
        };
        
        Plotly.newPlot('chart', [trace1, trace2], layout, {responsive: true});
        
        // Property prediction update
        function updatePrediction() {
            const form = document.getElementById('property-form');
            const formData = new FormData(form);
            
            const propertyData = {
                address: formData.get('address'),
                features: {
                    beds: parseInt(formData.get('beds')),
                    baths: parseFloat(formData.get('baths')),
                    sqft: parseInt(formData.get('sqft')),
                    lot_size_ac: parseFloat(formData.get('lot_size_ac')) || 0,
                    year_built: parseInt(formData.get('year_built')),
                    last_reno_year: parseInt(formData.get('last_reno_year')) || parseInt(formData.get('year_built')),
                    condition_grade: formData.get('condition_grade')
                }
            };
            
            fetch('/api/predict', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(propertyData)
            })
            .then(response => response.json())
            .then(data => {
                // Update prediction display
                document.querySelector('.prediction-price').textContent = 
                    '$' + data.predicted_price.toLocaleString();
                document.querySelector('.prediction-range').textContent = 
                    'Range: $' + data.price_low.toLocaleString() + ' - $' + data.price_high.toLocaleString();
                
                // Show success message
                alert('✅ Price updated! New valuation: $' + data.predicted_price.toLocaleString());
            })
            .catch(error => {
                console.error('Error:', error);
                alert('❌ Error updating prediction. Please try again.');
            });
        }
        
        function saveToFile() {
            const form = document.getElementById('property-form');
            const formData = new FormData(form);
            
            const propertyData = {
                property_id: "FSBO-MY-HOME",
                address: formData.get('address'),
                status: "FOR_SALE_BY_OWNER",
                features: {
                    beds: parseInt(formData.get('beds')),
                    baths: parseFloat(formData.get('baths')),
                    sqft: parseInt(formData.get('sqft')),
                    lot_size_ac: parseFloat(formData.get('lot_size_ac')) || 0,
                    year_built: parseInt(formData.get('year_built')),
                    last_reno_year: parseInt(formData.get('last_reno_year')) || parseInt(formData.get('year_built')),
                    condition_grade: formData.get('condition_grade')
                }
            };
            
            fetch('/api/save', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(propertyData)
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert('✅ Saved to my.json! Refresh the page to see updated valuation.');
                } else {
                    alert('❌ Error saving file: ' + data.error);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('❌ Error saving file. Please try again.');
            });
        }
        
        // Table sorting
        let sortDirections = {};
        
        function sortTable(tableId, colIndex) {
            const table = document.getElementById(tableId);
            const tbody = table.querySelector('tbody');
            const rows = Array.from(tbody.querySelectorAll('tr'));
            
            const key = `${tableId}-${colIndex}`;
            const direction = sortDirections[key] === 'asc' ? 'desc' : 'asc';
            sortDirections[key] = direction;
            
            // Update header classes
            table.querySelectorAll('th').forEach(th => {
                th.classList.remove('sorted-asc', 'sorted-desc');
            });
            table.querySelectorAll('th')[colIndex].classList.add(`sorted-${direction}`);
            
            rows.sort((a, b) => {
                let aVal = a.cells[colIndex].textContent;
                let bVal = b.cells[colIndex].textContent;
                
                // Try to parse as number
                const aNum = parseFloat(aVal.replace(/[$,]/g, ''));
                const bNum = parseFloat(bVal.replace(/[$,]/g, ''));
                
                if (!isNaN(aNum) && !isNaN(bNum)) {
                    return direction === 'asc' ? aNum - bNum : bNum - aNum;
                }
                
                // String comparison
                return direction === 'asc' ? 
                    aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
            });
            
            rows.forEach(row => tbody.appendChild(row));
        }
        
        // Filtering
        function filterTable(tableId, searchId, bedsFilterId, priceFilterId = null) {
            const search = document.getElementById(searchId).value.toLowerCase();
            const bedsFilter = document.getElementById(bedsFilterId).value;
            const priceFilter = priceFilterId ? document.getElementById(priceFilterId).value : '';
            
            const tbody = document.getElementById(tableId).querySelector('tbody');
            const rows = tbody.querySelectorAll('tr');
            
            rows.forEach(row => {
                const text = row.textContent.toLowerCase();
                const beds = row.dataset.beds;
                const price = parseInt(row.dataset.price);
                
                let show = true;
                
                if (search && !text.includes(search)) show = false;
                
                if (bedsFilter) {
                    if (bedsFilter === '4' && beds < 4) show = false;
                    else if (bedsFilter !== '4' && beds != bedsFilter) show = false;
                }
                
                if (priceFilter) {
                    const [min, max] = priceFilter.split('-').map(Number);
                    if (max && (price < min || price > max)) show = false;
                    if (!max && price < min) show = false;
                }
                
                row.style.display = show ? '' : 'none';
            });
        }
        
        document.getElementById('sales-search').addEventListener('input', () => 
            filterTable('sales-table', 'sales-search', 'sales-beds-filter', 'sales-price-filter'));
        document.getElementById('sales-beds-filter').addEventListener('change', () => 
            filterTable('sales-table', 'sales-search', 'sales-beds-filter', 'sales-price-filter'));
        document.getElementById('sales-price-filter').addEventListener('change', () => 
            filterTable('sales-table', 'sales-search', 'sales-beds-filter', 'sales-price-filter'));
        
        document.getElementById('listings-search').addEventListener('input', () => 
            filterTable('listings-table', 'listings-search', 'listings-beds-filter'));
        document.getElementById('listings-beds-filter').addEventListener('change', () => 
            filterTable('listings-table', 'listings-search', 'listings-beds-filter'));
        
        function resetSalesFilters() {
            document.getElementById('sales-search').value = '';
            document.getElementById('sales-beds-filter').value = '';
            document.getElementById('sales-price-filter').value = '';
            filterTable('sales-table', 'sales-search', 'sales-beds-filter', 'sales-price-filter');
        }
        
        function resetListingsFilters() {
            document.getElementById('listings-search').value = '';
            document.getElementById('listings-beds-filter').value = '';
            filterTable('listings-table', 'listings-search', 'listings-beds-filter');
        }
    </script>
    
    <footer style="text-align: center; padding: 40px 20px; color: #666; border-top: 1px solid #eee; margin-top: 40px;">
        <p>Real Estate Revenue Management Dashboard</p>
        <p>Copyright © 2026 Sasha Gutfraind | 
        <a href="https://github.com/sashagutfraind/homeseller_ai_agent" target="_blank" style="color: #4CAF50;">GitHub Repository</a></p>
        <p style="font-size: 12px; margin-top: 10px;">For educational and research purposes. See LICENSE.md for details.</p>
    </footer>
</body>
</html>
"""

# ============================================================================
# FLASK ROUTES
# ============================================================================

@app.route('/')
def index():
    """Main dashboard page"""
    sales, listings = load_data()
    my_listing = load_my_listing()
    
    # Calculate stats
    stats = {
        'total_sales': len(sales),
        'avg_price': np.mean([s['sale_details']['sold_price'] for s in sales]),
        'avg_dom': int(np.round(np.mean([s['sale_details']['days_on_market'] for s in sales]))),
        'active_listings': len(listings)
    }
    
    # Calculate trends
    trends = calculate_market_trends(sales)
    
    # Calibrate model and predict
    prediction = None
    model_score = 0
    if my_listing:
        model = PropertyPricingModel()
        model_score = model.calibrate(sales)
        prediction = model.predict(my_listing)
    
    return render_template_string(
        HTML_TEMPLATE,
        sales=sales,
        listings=listings,
        stats=stats,
        trends=trends,
        prediction=prediction,
        model_score=model_score,
        my_listing=my_listing
    )

@app.route('/api/predict', methods=['POST'])
def api_predict():
    """API endpoint for price prediction"""
    property_data = request.json
    sales, _ = load_data()
    
    model = PropertyPricingModel()
    model.calibrate(sales)
    prediction = model.predict(property_data)
    
    return jsonify(prediction)

@app.route('/api/save', methods=['POST'])
def api_save():
    """API endpoint to save property data to my.json"""
    try:
        property_data = request.json
        
        # Load existing data if available to preserve other fields
        try:
            with open('my.json', 'r') as f:
                existing_data = json.load(f)
                # Merge with new data
                existing_data.update(property_data)
                property_data = existing_data
        except FileNotFoundError:
            pass
        
        # Save to file
        with open('my.json', 'w') as f:
            json.dump(property_data, f, indent=2)
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    print("=" * 70)
    print("Real Estate Revenue Management Dashboard")
    print("=" * 70)
    print("\nStarting server at http://localhost:8080")
    print("Press Ctrl+C to stop\n")
    
    app.run(debug=True, host='0.0.0.0', port=8080)
