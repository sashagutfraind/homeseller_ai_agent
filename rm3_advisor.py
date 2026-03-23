#!/usr/bin/env python3
"""
Real Estate Price Management Advisor
Primary tool for FSBO sellers to manage pricing strategy

Copyright (c) 2026 Sasha Gutfraind
Repository: https://github.com/sashagutfraind/homeseller_ai_agent

This software is provided as-is for educational and research purposes.
See LICENSE.md for full license details.
"""

import json
from datetime import datetime, timedelta
from flask import Flask, render_template_string, jsonify, request
import os
import markdown

app = Flask(__name__)

# ============================================================================
# DATA LOADING
# ============================================================================

def load_my_listing():
    """Load FSBO listing data"""
    try:
        with open('my.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return None

def load_signals():
    """Load signals timeline from JSONL"""
    signals = []
    try:
        with open('data-generated/my_signals.jsonl', 'r') as f:
            for line in f:
                if line.strip():
                    signals.append(json.loads(line))
    except FileNotFoundError:
        pass
    return signals

def save_signal(signal_data):
    """Append a new signal to the JSONL file"""
    try:
        with open('data-generated/my_signals.jsonl', 'a') as f:
            f.write(json.dumps(signal_data) + '\n')
        return True
    except Exception as e:
        print(f"Error saving signal: {e}")
        return False

# ============================================================================
# ADVISOR LOGIC
# ============================================================================

class PriceAdvisor:
    """Analyzes signals and provides pricing recommendations"""
    
    def __init__(self, signals: list):
        self.signals = signals
        
    def analyze_traffic_trend(self, days: int = 7) -> dict:
        """Analyze traffic trend over the past N days"""
        if len(self.signals) < days:
            return {"trend": "insufficient_data", "change_pct": 0}
        
        recent_signals = self.signals[-days:]
        older_signals = self.signals[-days*2:-days] if len(self.signals) >= days*2 else self.signals[:days]
        
        # Calculate average CTR
        recent_ctr = sum(s["digital_signals"]["ctr"] for s in recent_signals) / len(recent_signals)
        older_ctr = sum(s["digital_signals"]["ctr"] for s in older_signals) / len(older_signals) if older_signals else recent_ctr
        
        # Calculate average showings
        recent_showings = sum(s["showing_signals"]["showings_requested"] for s in recent_signals) / len(recent_signals)
        older_showings = sum(s["showing_signals"]["showings_requested"] for s in older_signals) / len(older_signals) if older_signals else recent_showings
        
        # Determine trend
        ctr_change = ((recent_ctr - older_ctr) / older_ctr * 100) if older_ctr > 0 else 0
        showing_change = ((recent_showings - older_showings) / older_showings * 100) if older_showings > 0 else 0
        
        avg_change = (ctr_change + showing_change) / 2
        
        if avg_change < -15:
            trend = "declining"
        elif avg_change < -5:
            trend = "slowing"
        elif avg_change > 15:
            trend = "increasing"
        elif avg_change > 5:
            trend = "stable_positive"
        else:
            trend = "stable"
        
        return {
            "trend": trend,
            "change_pct": round(avg_change, 1),
            "recent_ctr": round(recent_ctr, 2),
            "recent_showings": round(recent_showings, 1),
            "older_ctr": round(older_ctr, 2),
            "older_showings": round(older_showings, 1)
        }
    
    def get_recommendation(self) -> dict:
        """Generate pricing recommendation"""
        if not self.signals:
            return {
                "action": "wait",
                "reason": "No signals data available yet",
                "price_adjustment_pct": 0,
                "confidence": "low"
            }
        
        latest = self.signals[-1]
        days_on_market = latest["day"]
        current_price = latest["price"]
        
        # Analyze traffic
        traffic = self.analyze_traffic_trend(days=7)
        
        # Get latest signals
        ctr = latest["digital_signals"]["ctr"]
        showings = latest["showing_signals"]["showings_requested"]
        second_showings = latest["showing_signals"]["second_showings"]
        
        # Decision logic
        if traffic["trend"] in ["declining", "slowing"]:
            if days_on_market > 14:
                return {
                    "action": "reduce_price",
                    "reason": f"Traffic has {traffic['trend']} by {abs(traffic['change_pct']):.1f}% over the past week and property has been on market for {days_on_market} days",
                    "price_adjustment_pct": -5.0,
                    "new_price": int(current_price * 0.95),
                    "confidence": "high",
                    "urgency": "high"
                }
            else:
                return {
                    "action": "reduce_price",
                    "reason": f"Traffic has {traffic['trend']} by {abs(traffic['change_pct']):.1f}% over the past week",
                    "price_adjustment_pct": -5.0,
                    "new_price": int(current_price * 0.95),
                    "confidence": "medium",
                    "urgency": "medium"
                }
        
        if ctr < 1.5 and showings < 3:
            return {
                "action": "reduce_price",
                "reason": f"Low engagement: CTR is {ctr}% (target: >1.5%) and only {showings} showing requests",
                "price_adjustment_pct": -5.0,
                "new_price": int(current_price * 0.95),
                "confidence": "high",
                "urgency": "high"
            }
        
        if days_on_market > 21 and second_showings == 0:
            return {
                "action": "reduce_price",
                "reason": f"Property has been on market for {days_on_market} days with no second showings - buyers not seriously interested",
                "price_adjustment_pct": -5.0,
                "new_price": int(current_price * 0.95),
                "confidence": "high",
                "urgency": "high"
            }
        
        if traffic["trend"] == "stable" and showings >= 3:
            return {
                "action": "hold",
                "reason": f"Traffic is stable with {showings} showing requests per week - maintain current price",
                "price_adjustment_pct": 0,
                "confidence": "medium",
                "urgency": "low"
            }
        
        if traffic["trend"] in ["increasing", "stable_positive"]:
            return {
                "action": "hold",
                "reason": f"Traffic is {traffic['trend']} - current price is attracting buyers",
                "price_adjustment_pct": 0,
                "confidence": "high",
                "urgency": "low"
            }
        
        return {
            "action": "monitor",
            "reason": "Continue monitoring signals for a few more days",
            "price_adjustment_pct": 0,
            "confidence": "low",
            "urgency": "low"
        }

# ============================================================================
# HTML TEMPLATE
# ============================================================================

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Price Management Advisor (PoC/Alpha)</title>
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
        
        .price-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }
        
        .current-price {
            font-size: 48px;
            font-weight: bold;
            color: #2e7d32;
        }
        
        .days-on-market {
            font-size: 18px;
            color: #666;
        }
        
        .price-history {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            margin-top: 15px;
        }
        
        .price-point {
            background: #e8f5e9;
            padding: 10px 15px;
            border-radius: 4px;
            border-left: 3px solid #4CAF50;
        }
        
        .price-point.reduced {
            background: #fff3e0;
            border-left-color: #ff9800;
        }
        
        .recommendation-box {
            padding: 25px;
            border-radius: 8px;
            margin-bottom: 20px;
        }
        
        .recommendation-box.reduce {
            background: linear-gradient(135deg, #ff6b6b 0%, #ee5a6f 100%);
            color: white;
        }
        
        .recommendation-box.hold {
            background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%);
            color: white;
        }
        
        .recommendation-box.monitor {
            background: linear-gradient(135deg, #2196F3 0%, #1976D2 100%);
            color: white;
        }
        
        .recommendation-action {
            font-size: 32px;
            font-weight: bold;
            margin-bottom: 10px;
        }
        
        .recommendation-reason {
            font-size: 18px;
            margin-bottom: 15px;
            opacity: 0.95;
        }
        
        .recommendation-details {
            background: rgba(255,255,255,0.2);
            padding: 15px;
            border-radius: 4px;
            margin-top: 15px;
        }
        
        .urgency-badge {
            display: inline-block;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 14px;
            font-weight: 500;
            margin-top: 10px;
        }
        
        .urgency-high {
            background: #d32f2f;
            color: white;
        }
        
        .urgency-medium {
            background: #f57c00;
            color: white;
        }
        
        .urgency-low {
            background: #388e3c;
            color: white;
        }
        
        .stale-warning {
            background: #fff3cd;
            border: 2px solid #ffc107;
            color: #856404;
            padding: 15px;
            border-radius: 4px;
            margin-bottom: 15px;
            font-size: 14px;
        }
        
        .stale-warning strong {
            color: #856404;
        }
        
        .controls {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
        }
        
        button, .btn {
            padding: 12px 24px;
            border: none;
            border-radius: 4px;
            font-size: 16px;
            font-weight: 500;
            cursor: pointer;
            text-decoration: none;
            display: inline-block;
        }
        
        .btn-primary {
            background: #4CAF50;
            color: white;
        }
        
        .btn-primary:hover {
            background: #45a049;
        }
        
        .btn-secondary {
            background: #757575;
            color: white;
        }
        
        .btn-secondary:hover {
            background: #616161;
        }
        
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
            border-bottom: 2px solid #dee2e6;
        }
        
        td {
            padding: 10px 12px;
            border-bottom: 1px solid #eee;
        }
        
        tr:hover { background: #f8f9fa; }
        
        .metric-good { color: #2e7d32; font-weight: 600; }
        .metric-warning { color: #f57c00; font-weight: 600; }
        .metric-bad { color: #d32f2f; font-weight: 600; }
        
        #chart { height: 400px; margin-top: 20px; }
        
        footer {
            text-align: center;
            padding: 40px 20px;
            color: #666;
            border-top: 1px solid #eee;
            margin-top: 40px;
        }
        
        footer a {
            color: #4CAF50;
            text-decoration: none;
        }
        
        footer a:hover {
            text-decoration: underline;
        }
        
        /* Modal styles */
        .modal {
            display: none;
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            overflow: auto;
            background-color: rgba(0,0,0,0.5);
        }
        
        .modal-content {
            background-color: white;
            margin: 5% auto;
            padding: 30px;
            border-radius: 8px;
            width: 90%;
            max-width: 800px;
            max-height: 80vh;
            overflow-y: auto;
        }
        
        .modal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 2px solid #4CAF50;
        }
        
        .modal-header h2 {
            margin: 0;
            color: #333;
        }
        
        .close {
            font-size: 32px;
            font-weight: bold;
            color: #999;
            cursor: pointer;
            line-height: 1;
        }
        
        .close:hover {
            color: #333;
        }
        
        .form-group {
            margin-bottom: 20px;
        }
        
        .form-group label {
            display: block;
            font-weight: 600;
            margin-bottom: 5px;
            color: #333;
        }
        
        .form-group input {
            width: 100%;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
        }
        
        .form-group input:focus {
            outline: none;
            border-color: #4CAF50;
        }
        
        .form-section {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 4px;
            margin-bottom: 20px;
        }
        
        .form-section h3 {
            margin: 0 0 15px 0;
            color: #333;
            font-size: 16px;
        }
        
        .form-row {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
        }
        
        .btn-submit {
            background: #4CAF50;
            color: white;
            padding: 12px 30px;
            border: none;
            border-radius: 4px;
            font-size: 16px;
            font-weight: 500;
            cursor: pointer;
            width: 100%;
        }
        
        .btn-submit:hover {
            background: #45a049;
        }
        
        .success-message {
            background: #d4edda;
            color: #155724;
            padding: 15px;
            border-radius: 4px;
            margin-bottom: 20px;
            display: none;
        }
        
        .error-message {
            background: #f8d7da;
            color: #721c24;
            padding: 15px;
            border-radius: 4px;
            margin-bottom: 20px;
            display: none;
        }
    </style>
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
</head>
<body>
    <div class="container">
        <h1>🏠 Price Management Advisor (PoC/Alpha)</h1>
        <p class="subtitle">AI-Powered pricing strategy for sellers</p>
        
        <!-- Current Price & History -->
        <div class="card">
            <h2>💰 Current Pricing</h2>
            <div class="price-header">
                <div>
                    <div class="current-price">${{ "{:,.0f}".format(current_price) }}</div>
                    <div class="days-on-market">Day {{ days_on_market }} on Market</div>
                </div>
                <div class="controls">
                    <button onclick="showAddSignalModal()" class="btn btn-primary">➕ Add New Signal</button>
                    <a href="/strategy" class="btn btn-secondary" target="_blank">📖 Read Strategy Guide</a>
                    <a href="/theory" class="btn btn-secondary" target="_blank">📚 Read Pricing Theory</a>
                </div>
            </div>
            
            <h3 style="margin-top: 20px; margin-bottom: 10px;">Price History</h3>
            <div class="price-history">
                {% for point in price_history %}
                <div class="price-point {% if point.reduced %}reduced{% endif %}">
                    <strong>{{ point.date }}</strong><br>
                    ${{ "{:,.0f}".format(point.price) }}
                    {% if point.reduced %}
                    <br><span style="color: #f57c00;">↓ {{ point.reduction_pct }}%</span>
                    {% endif %}
                </div>
                {% endfor %}
            </div>
        </div>
        
        <!-- Recommendation -->
        <div class="card">
            <h2>🎯 Pricing Recommendation</h2>
            
            {% if recommendation.is_stale %}
            <div class="stale-warning">
                ⚠️ <strong>Outdated Recommendation:</strong> This recommendation is based on data through {{ recommendation.last_signal_date }}. 
                New signals have been added since then. Refresh the page to see updated recommendations.
            </div>
            {% endif %}
            
            <div class="recommendation-box {{ recommendation.action }}">
                <div class="recommendation-action">
                    {% if recommendation.action == 'reduce_price' %}
                    ⚠️ REDUCE PRICE
                    {% elif recommendation.action == 'hold' %}
                    ✅ HOLD CURRENT PRICE
                    {% else %}
                    👀 CONTINUE MONITORING
                    {% endif %}
                </div>
                <div class="recommendation-reason">{{ recommendation.reason }}</div>
                
                {% if recommendation.action == 'reduce_price' %}
                <div class="recommendation-details">
                    <strong>Recommended Adjustment:</strong> {{ recommendation.price_adjustment_pct }}%<br>
                    <strong>New Price:</strong> ${{ "{:,.0f}".format(recommendation.new_price) }}<br>
                    <strong>Confidence:</strong> {{ recommendation.confidence|capitalize }}
                </div>
                {% endif %}
                
                <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 15px;">
                    <span class="urgency-badge urgency-{{ recommendation.urgency }}">
                        {{ recommendation.urgency|upper }} URGENCY
                    </span>
                    <span style="opacity: 0.9; font-size: 14px;">
                        Based on {{ recommendation.signals_count }} signals through {{ recommendation.last_signal_date }}
                    </span>
                </div>
            </div>
        </div>
        
        <!-- Signals Chart -->
        <div class="card">
            <h2>📈 Market Signals Trend</h2>
            <div id="chart"></div>
        </div>
        
        <!-- Signals Table -->
        <div class="card">
            <h2>📊 Detailed Signals (Last 7 Days)</h2>
            <div style="overflow-x: auto;">
                <table>
                    <thead>
                        <tr>
                            <th>Date</th>
                            <th>Price</th>
                            <th>CTR %</th>
                            <th>Impressions</th>
                            <th>Clicks</th>
                            <th>Saves</th>
                            <th>Showings</th>
                            <th>2nd Showings</th>
                            <th>Mortgage Rate</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for signal in recent_signals %}
                        <tr>
                            <td>{{ signal.date }}</td>
                            <td>${{ "{:,.0f}".format(signal.price) }}</td>
                            <td class="{% if signal.digital_signals.ctr >= 1.5 %}metric-good{% elif signal.digital_signals.ctr >= 1.0 %}metric-warning{% else %}metric-bad{% endif %}">
                                {{ signal.digital_signals.ctr }}%
                            </td>
                            <td>{{ signal.digital_signals.impressions }}</td>
                            <td>{{ signal.digital_signals.clicks }}</td>
                            <td>{{ signal.digital_signals.saves }}</td>
                            <td class="{% if signal.showing_signals.showings_requested >= 3 %}metric-good{% elif signal.showing_signals.showings_requested >= 2 %}metric-warning{% else %}metric-bad{% endif %}">
                                {{ signal.showing_signals.showings_requested }}
                            </td>
                            <td>{{ signal.showing_signals.second_showings }}</td>
                            <td>{{ signal.macro_signals.mortgage_rate_30yr }}%</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
        
        <!-- Traffic Analysis -->
        <div class="card">
            <h2>📉 Traffic Analysis (Past 7 Days)</h2>
            <p><strong>Trend:</strong> {{ traffic.trend|replace('_', ' ')|title }}</p>
            <p><strong>Change:</strong> {{ traffic.change_pct }}%</p>
            <p><strong>Recent CTR:</strong> {{ traffic.recent_ctr }}% (Previous: {{ traffic.older_ctr }}%)</p>
            <p><strong>Recent Showings:</strong> {{ traffic.recent_showings }} per day (Previous: {{ traffic.older_showings }})</p>
        </div>
    </div>
    
    <!-- Add Signal Modal -->
    <div id="addSignalModal" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                <h2>➕ Add New Market Signal</h2>
                <span class="close" onclick="closeAddSignalModal()">&times;</span>
            </div>
            
            <div id="successMessage" class="success-message">
                Signal added successfully! Refreshing page...
            </div>
            
            <div id="errorMessage" class="error-message">
                Error adding signal. Please try again.
            </div>
            
            <form id="addSignalForm" onsubmit="submitSignal(event)">
                <div class="form-group">
                    <label>Date</label>
                    <input type="date" id="signal_date" required>
                </div>
                
                <div class="form-group">
                    <label>Price ($)</label>
                    <input type="number" id="signal_price" required min="0" step="1000" value="{{ current_price }}">
                </div>
                
                <div class="form-section">
                    <h3>📱 Digital Signals</h3>
                    <div class="form-row">
                        <div class="form-group">
                            <label>Impressions</label>
                            <input type="number" id="impressions" required min="0" value="0">
                        </div>
                        <div class="form-group">
                            <label>Clicks</label>
                            <input type="number" id="clicks" required min="0" value="0">
                        </div>
                    </div>
                    <div class="form-row">
                        <div class="form-group">
                            <label>Saves</label>
                            <input type="number" id="saves" required min="0" value="0">
                        </div>
                        <div class="form-group">
                            <label>CTR (%)</label>
                            <input type="number" id="ctr" required min="0" max="100" step="0.1" value="0">
                        </div>
                    </div>
                </div>
                
                <div class="form-section">
                    <h3>🏠 Showing Signals</h3>
                    <div class="form-row">
                        <div class="form-group">
                            <label>Showings Requested</label>
                            <input type="number" id="showings_requested" required min="0" value="0">
                        </div>
                        <div class="form-group">
                            <label>Showings Completed</label>
                            <input type="number" id="showings_completed" required min="0" value="0">
                        </div>
                    </div>
                    <div class="form-group">
                        <label>Second Showings</label>
                        <input type="number" id="second_showings" required min="0" value="0">
                    </div>
                </div>
                
                <div class="form-section">
                    <h3>🏘️ Competitive Signals</h3>
                    <div class="form-row">
                        <div class="form-group">
                            <label>New Listings (Neighborhood)</label>
                            <input type="number" id="new_listings" required min="0" value="0">
                        </div>
                        <div class="form-group">
                            <label>Pending Sales (Neighborhood)</label>
                            <input type="number" id="pending_sales" required min="0" value="0">
                        </div>
                    </div>
                    <div class="form-group">
                        <label>Price Reductions (Neighborhood)</label>
                        <input type="number" id="price_reductions" required min="0" value="0">
                    </div>
                </div>
                
                <div class="form-section">
                    <h3>📊 Macro Signals</h3>
                    <div class="form-row">
                        <div class="form-group">
                            <label>Mortgage Rate 30yr (%)</label>
                            <input type="number" id="mortgage_rate" required min="0" max="20" step="0.01" value="6.5">
                        </div>
                        <div class="form-group">
                            <label>Inventory Change (%)</label>
                            <input type="number" id="inventory_change" required step="0.1" value="0">
                        </div>
                    </div>
                    <div class="form-group">
                        <label>Absorption Rate (%)</label>
                        <input type="number" id="absorption_rate" required min="0" max="100" step="0.1" value="15">
                    </div>
                </div>
                
                <div class="form-group">
                    <label>Notes (Optional)</label>
                    <input type="text" id="notes" placeholder="Any observations or feedback from visitors">
                </div>
                
                <button type="submit" class="btn-submit">Add Signal</button>
            </form>
        </div>
    </div>
    
    <footer>
        <p>Real Estate Price Management Advisor</p>
        <p>Copyright © 2026 Sasha Gutfraind | 
        <a href="https://github.com/sashagutfraind/homeseller_ai_agent" target="_blank">GitHub Repository</a></p>
        <p style="font-size: 12px; margin-top: 10px;">For educational and research purposes. See LICENSE.md for details.</p>
    </footer>
    
    <script>
        // Signals chart
        const signals = {{ signals|tojson }};
        
        const dates = signals.map(s => s.date);
        const prices = signals.map(s => s.price);
        const ctrs = signals.map(s => s.digital_signals.ctr);
        const showings = signals.map(s => s.showing_signals.showings_requested);
        
        const trace1 = {
            x: dates,
            y: prices,
            name: 'Price',
            type: 'scatter',
            mode: 'lines+markers',
            line: { color: '#2e7d32', width: 3 },
            yaxis: 'y'
        };
        
        const trace2 = {
            x: dates,
            y: ctrs,
            name: 'CTR %',
            type: 'scatter',
            mode: 'lines+markers',
            line: { color: '#1976D2', width: 2 },
            yaxis: 'y2'
        };
        
        const trace3 = {
            x: dates,
            y: showings,
            name: 'Showings',
            type: 'scatter',
            mode: 'lines+markers',
            line: { color: '#f57c00', width: 2 },
            yaxis: 'y3'
        };
        
        const layout = {
            title: 'Price, CTR, and Showings Over Time',
            xaxis: { title: 'Date' },
            yaxis: {
                title: 'Price ($)',
                tickformat: '$,.0f',
                side: 'left'
            },
            yaxis2: {
                title: 'CTR %',
                overlaying: 'y',
                side: 'right',
                position: 0.85
            },
            yaxis3: {
                title: 'Showings',
                overlaying: 'y',
                side: 'right'
            },
            hovermode: 'x unified',
            showlegend: true,
            legend: { x: 0, y: 1.1, orientation: 'h' }
        };
        
        Plotly.newPlot('chart', [trace1, trace2, trace3], layout, {responsive: true});
        
        // Modal functions
        function showAddSignalModal() {
            document.getElementById('addSignalModal').style.display = 'block';
            // Set today's date as default
            const today = new Date().toISOString().split('T')[0];
            document.getElementById('signal_date').value = today;
        }
        
        function closeAddSignalModal() {
            document.getElementById('addSignalModal').style.display = 'none';
            document.getElementById('successMessage').style.display = 'none';
            document.getElementById('errorMessage').style.display = 'none';
        }
        
        // Close modal when clicking outside
        window.onclick = function(event) {
            const modal = document.getElementById('addSignalModal');
            if (event.target == modal) {
                closeAddSignalModal();
            }
        }
        
        async function submitSignal(event) {
            event.preventDefault();
            
            const signalData = {
                date: document.getElementById('signal_date').value,
                price: parseInt(document.getElementById('signal_price').value),
                digital_signals: {
                    impressions: parseInt(document.getElementById('impressions').value),
                    clicks: parseInt(document.getElementById('clicks').value),
                    saves: parseInt(document.getElementById('saves').value),
                    ctr: parseFloat(document.getElementById('ctr').value)
                },
                showing_signals: {
                    showings_requested: parseInt(document.getElementById('showings_requested').value),
                    showings_completed: parseInt(document.getElementById('showings_completed').value),
                    second_showings: parseInt(document.getElementById('second_showings').value)
                },
                competitive_signals: {
                    new_listings_neighborhood: parseInt(document.getElementById('new_listings').value),
                    pending_sales_neighborhood: parseInt(document.getElementById('pending_sales').value),
                    price_reductions_neighborhood: parseInt(document.getElementById('price_reductions').value)
                },
                macro_signals: {
                    mortgage_rate_30yr: parseFloat(document.getElementById('mortgage_rate').value),
                    inventory_change_pct: parseFloat(document.getElementById('inventory_change').value),
                    absorption_rate_pct: parseFloat(document.getElementById('absorption_rate').value)
                },
                notes: document.getElementById('notes').value
            };
            
            try {
                const response = await fetch('/api/add_signal', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(signalData)
                });
                
                const result = await response.json();
                
                if (result.success) {
                    document.getElementById('successMessage').style.display = 'block';
                    document.getElementById('errorMessage').style.display = 'none';
                    setTimeout(() => {
                        location.reload();
                    }, 1500);
                } else {
                    document.getElementById('errorMessage').style.display = 'block';
                    document.getElementById('errorMessage').textContent = result.error || 'Error adding signal';
                    document.getElementById('successMessage').style.display = 'none';
                }
            } catch (error) {
                document.getElementById('errorMessage').style.display = 'block';
                document.getElementById('errorMessage').textContent = 'Network error: ' + error.message;
                document.getElementById('successMessage').style.display = 'none';
            }
        }
    </script>
</body>
</html>
"""

# ============================================================================
# FLASK ROUTES
# ============================================================================

@app.route('/')
def index():
    """Main advisor page"""
    my_listing = load_my_listing()
    signals = load_signals()
    
    if not signals:
        return "No signals data found. Please run rm1_data_gen.py first.", 404
    
    # Get current price and days on market
    latest = signals[-1]
    current_price = latest["price"]
    days_on_market = latest["day"]
    
    # Build price history
    price_history = []
    prev_price = signals[0]["price"]
    for signal in signals:
        if signal["price"] != prev_price or signal["day"] == 0:
            reduction_pct = 0
            if prev_price > 0 and signal["price"] < prev_price:
                reduction_pct = round((prev_price - signal["price"]) / prev_price * 100, 1)
            
            price_history.append({
                "date": signal["date"],
                "price": signal["price"],
                "reduced": signal["price"] < prev_price,
                "reduction_pct": reduction_pct
            })
            prev_price = signal["price"]
    
    # Get recommendation
    advisor = PriceAdvisor(signals)
    recommendation = advisor.get_recommendation()
    traffic = advisor.analyze_traffic_trend(days=7)
    
    # Add metadata to recommendation
    recommendation['last_signal_date'] = latest['date']
    recommendation['signals_count'] = len(signals)
    recommendation['is_stale'] = False  # Will be set to True by JavaScript if page was loaded before last signal
    
    # Get recent signals (last 7 days)
    recent_signals = signals[-7:]
    
    return render_template_string(
        HTML_TEMPLATE,
        current_price=current_price,
        days_on_market=days_on_market,
        price_history=price_history,
        recommendation=recommendation,
        traffic=traffic,
        signals=signals,
        recent_signals=recent_signals
    )

@app.route('/strategy')
def strategy():
    """Render STRATEGY.md as HTML"""
    try:
        with open('STRATEGY.md', 'r') as f:
            content = f.read()
        html_content = markdown.markdown(content, extensions=['tables', 'fenced_code'])
        
        return render_template_string("""
<!DOCTYPE html>
<html>
<head>
    <title>Strategy Guide - Price Management</title>
    <meta charset="utf-8">
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            max-width: 900px;
            margin: 40px auto;
            padding: 20px;
            line-height: 1.6;
            background: #f5f5f5;
        }
        .content {
            background: white;
            padding: 40px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        h1 { color: #2e7d32; border-bottom: 3px solid #4CAF50; padding-bottom: 10px; }
        h2 { color: #333; margin-top: 30px; border-bottom: 2px solid #e0e0e0; padding-bottom: 8px; }
        h3 { color: #555; margin-top: 25px; }
        h4 { color: #666; margin-top: 20px; }
        table { border-collapse: collapse; width: 100%; margin: 20px 0; }
        th, td { border: 1px solid #ddd; padding: 12px; text-align: left; }
        th { background: #f8f9fa; font-weight: 600; }
        tr:hover { background: #f8f9fa; }
        code { background: #f4f4f4; padding: 2px 6px; border-radius: 3px; font-family: 'Courier New', monospace; }
        pre { background: #f4f4f4; padding: 15px; border-radius: 4px; overflow-x: auto; }
        a { color: #4CAF50; text-decoration: none; }
        a:hover { text-decoration: underline; }
        .back-link { display: inline-block; margin-bottom: 20px; padding: 10px 20px; background: #4CAF50; color: white; border-radius: 4px; }
        .back-link:hover { background: #45a049; text-decoration: none; }
    </style>
    <script src="https://polyfill.io/v3/polyfill.min.js?features=es6"></script>
    <script id="MathJax-script" async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
    <script>
        window.MathJax = {
            tex: {
                inlineMath: [['$', '$']],
                displayMath: [['$$', '$$']]
            }
        };
    </script>
</head>
<body>
    <a href="/" class="back-link">← Back to Advisor</a>
    <div class="content">
        {{ content|safe }}
    </div>
</body>
</html>
        """, content=html_content)
    except FileNotFoundError:
        return "STRATEGY.md not found", 404

@app.route('/theory')
def theory():
    """Render THEORY.md as HTML"""
    try:
        with open('THEORY.md', 'r') as f:
            content = f.read()
        html_content = markdown.markdown(content, extensions=['tables', 'fenced_code'])
        
        return render_template_string("""
<!DOCTYPE html>
<html>
<head>
    <title>Pricing Theory - Price Management</title>
    <meta charset="utf-8">
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            max-width: 900px;
            margin: 40px auto;
            padding: 20px;
            line-height: 1.6;
            background: #f5f5f5;
        }
        .content {
            background: white;
            padding: 40px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        h1 { color: #2e7d32; border-bottom: 3px solid #4CAF50; padding-bottom: 10px; }
        h2 { color: #333; margin-top: 30px; border-bottom: 2px solid #e0e0e0; padding-bottom: 8px; }
        h3 { color: #555; margin-top: 25px; }
        h4 { color: #666; margin-top: 20px; }
        table { border-collapse: collapse; width: 100%; margin: 20px 0; }
        th, td { border: 1px solid #ddd; padding: 12px; text-align: left; }
        th { background: #f8f9fa; font-weight: 600; }
        tr:hover { background: #f8f9fa; }
        code { background: #f4f4f4; padding: 2px 6px; border-radius: 3px; font-family: 'Courier New', monospace; }
        pre { background: #f4f4f4; padding: 15px; border-radius: 4px; overflow-x: auto; }
        a { color: #4CAF50; text-decoration: none; }
        a:hover { text-decoration: underline; }
        .back-link { display: inline-block; margin-bottom: 20px; padding: 10px 20px; background: #4CAF50; color: white; border-radius: 4px; }
        .back-link:hover { background: #45a049; text-decoration: none; }
    </style>
    <script src="https://polyfill.io/v3/polyfill.min.js?features=es6"></script>
    <script id="MathJax-script" async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
    <script>
        window.MathJax = {
            tex: {
                inlineMath: [['$', '$']],
                displayMath: [['$$', '$$']]
            }
        };
    </script>
</head>
<body>
    <a href="/" class="back-link">← Back to Advisor</a>
    <div class="content">
        {{ content|safe }}
    </div>
</body>
</html>
        """, content=html_content)
    except FileNotFoundError:
        return "THEORY.md not found", 404

@app.route('/api/recommendation')
def api_recommendation():
    """API endpoint for recommendation"""
    signals = load_signals()
    if not signals:
        return jsonify({"error": "No signals data"}), 404
    
    advisor = PriceAdvisor(signals)
    recommendation = advisor.get_recommendation()
    
    return jsonify(recommendation)

@app.route('/api/add_signal', methods=['POST'])
def api_add_signal():
    """API endpoint to add a new signal"""
    try:
        data = request.json
        
        # Load existing signals to calculate day number
        signals = load_signals()
        
        if signals:
            last_day = signals[-1].get('day', 0)
            new_day = last_day + 1
        else:
            new_day = 0
        
        # Build the signal object matching the original format
        signal_data = {
            "date": data['date'],
            "day": new_day,
            "price": data['price'],
            "digital_signals": {
                "impressions": data['digital_signals']['impressions'],
                "clicks": data['digital_signals']['clicks'],
                "saves": data['digital_signals']['saves'],
                "shares": 0,
                "ctr": data['digital_signals']['ctr'],
                "save_rate": (data['digital_signals']['saves'] / data['digital_signals']['clicks'] * 100) if data['digital_signals']['clicks'] > 0 else 0.0
            },
            "showing_signals": {
                "showings_requested": data['showing_signals']['showings_requested'],
                "showings_completed": data['showing_signals']['showings_completed'],
                "second_showings": data['showing_signals']['second_showings'],
                "no_shows": data['showing_signals']['showings_requested'] - data['showing_signals']['showings_completed']
            },
            "competitive_signals": {
                "new_listings_this_week": data['competitive_signals']['new_listings_neighborhood'],
                "pending_sales_this_week": data['competitive_signals']['pending_sales_neighborhood'],
                "price_reductions_nearby": data['competitive_signals']['price_reductions_neighborhood'],
                "days_on_market_avg_zip": 0  # Not collected in form
            },
            "macro_signals": {
                "mortgage_rate_30yr": data['macro_signals']['mortgage_rate_30yr'],
                "inventory_change_pct": data['macro_signals']['inventory_change_pct'],
                "median_sale_price_zip": 0,  # Not collected in form
                "absorption_rate_pct": data['macro_signals']['absorption_rate_pct']
            },
            "agent_feedback": [],
            "self_note": data.get('notes', ''),
            "visitor_notes": []
        }
        
        # Save to file
        if save_signal(signal_data):
            return jsonify({"success": True, "day": new_day})
        else:
            return jsonify({"success": False, "error": "Failed to save signal"}), 500
            
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    print("=" * 70)
    print("Price Management Advisor")
    print("=" * 70)
    print("\nStarting server at http://localhost:8081")
    print("Press Ctrl+C to stop\n")
    
    app.run(debug=True, host='0.0.0.0', port=8081)
