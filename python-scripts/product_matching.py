#!/usr/bin/env python3
"""
Simple Invoice processing service with basic product matching
"""

from flask import Flask, request, jsonify
from datetime import datetime, timezone, timedelta
import os
from matching_methods.basic import basic_matching
from matching_methods.fuzzy import fuzzy_matching
import time

app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    # Create UTC+8 timezone
    utc_plus_8 = timezone(timedelta(hours=8))
    
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now(utc_plus_8).isoformat(),
        "service": "invoice-agent-python",
        "features": ["basic_matching", "fuzzy_matching"]
    })

@app.route('/process-invoice', methods=['POST'])
def process_invoice():
    """Process invoice data sent from n8n with basic matching"""
    start_time = time.time()
    try:
        data = request.get_json()
        
        invoice_data = data.get('invoice_data', {})
        product_db = data.get('product_db', [])
        match_method = data.get('match_method', 'basic') # Default to basic
        
        if match_method == 'fuzzy':
            processed_data = fuzzy_matching(invoice_data, product_db)
        else:
            processed_data = basic_matching(invoice_data, product_db)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        return jsonify({
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "processing_time": processing_time,
            "processing_stats": get_processing_stats(processed_data),
            "processed_data": processed_data
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

def get_processing_stats(invoice_data):
    """Get processing statistics"""
    items = invoice_data.get('items', [])
    matched_items = len([item for item in items if item.get('product_id')])
    unmatched_items = len(items) - matched_items
    
    stats = {
        'total_items': len(items),
        'matched_items': matched_items,
        'unmatched_items': unmatched_items,
    }

    # Add match score stats if available from fuzzy matching
    if items and 'match_score' in items[0]:
        scores = [item['match_score'] for item in items if 'match_score' in item]
        if scores:
            stats['average_match_score'] = sum(scores) / len(scores)
            stats['min_match_score'] = min(scores)
            stats['max_match_score'] = max(scores)

    return stats

if __name__ == '__main__':
    # Adjust the path to be relative to the script's location
    shared_dir = os.path.join(os.path.dirname(__file__), 'shared')
    os.makedirs(shared_dir, exist_ok=True)
    
    print("🚀 Starting Simple Invoice Agent Python Service...")
    print("📊 Available endpoints:")
    print("  GET  /health - Health check")
    print("  POST /process-invoice - Basic invoice processing with exact matching")
    
    app.run(host='0.0.0.0', port=5000, debug=True) 