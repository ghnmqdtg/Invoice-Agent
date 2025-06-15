#!/usr/bin/env python3
"""
Simple Invoice processing service with basic product matching
"""

from flask import Flask, request, jsonify
from datetime import datetime, timezone, timedelta
import os
import re

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
        "features": ["basic_matching"]
    })

@app.route('/process-invoice', methods=['POST'])
def process_invoice():
    """Process invoice data sent from n8n with basic matching"""
    try:
        data = request.get_json()
        
        invoice_data = data.get('invoice_data', {})
        product_db = data.get('product_db', [])
        
        processed_data = basic_matching(invoice_data, product_db)
        
        return jsonify({
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "processing_stats": get_processing_stats(processed_data),
            "processed_data": processed_data
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

def basic_matching(invoice_data, product_db):
    """Enhanced invoice processing with basic exact matching"""
    if 'items' not in invoice_data:
        return invoice_data
    
    enhanced_items = []
    match_stats = {"exact_matches": 0, "no_matches": 0}
    
    for item in invoice_data['items']:
        enhanced_item = basic_match_product(item, product_db)
        
        # Track matching statistics
        if enhanced_item.get('product_id'):
            match_stats["exact_matches"] += 1
        else:
            match_stats["no_matches"] += 1
        
        # Override subtotal
        if enhanced_item.get('quantity') and enhanced_item.get('unit_price'):
            enhanced_item['subtotal'] = enhanced_item['quantity'] * enhanced_item['unit_price']
        
        enhanced_items.append(enhanced_item)
    
    invoice_data['items'] = enhanced_items
    invoice_data['match_statistics'] = match_stats
    invoice_data['processed_at'] = datetime.now().isoformat()
    
    return invoice_data

def basic_match_product(item, product_db):
    """Basic exact string matching with support for concatenated names"""
    product_name = item.get('product_name', '').strip().lower()
    enhanced_item = item.copy()
    
    # Rename product_name to original_name
    if 'product_name' in enhanced_item:
        enhanced_item['original_name'] = enhanced_item.pop('product_name')
    
    for product in product_db:
        product_names = product.get('product_name', '').strip().lower().split('/')
        # Remove any (unit) from product names for comparison, for example: 鴻禧菇(包) -> 鴻禧菇
        cleaned_names = [re.sub(r'\([^)]*\)', '', name.strip()) for name in product_names]
        
        # Check for exact match with any individual part
        if product_name in cleaned_names:
            enhanced_item['product_id'] = product.get('product_id')
            enhanced_item['matched_name'] = product.get('product_name')
            enhanced_item['product_unit'] = product.get('unit')
            enhanced_item['product_currency'] = product.get('currency')
            break
        
        # Check for concatenated match (e.g., "豬板油二層油" matches "豬板油/二層油")
        concatenated = ''.join(cleaned_names)
        if product_name == concatenated:
            enhanced_item['product_id'] = product.get('product_id')
            enhanced_item['matched_name'] = product.get('product_name')
            enhanced_item['product_unit'] = product.get('unit')
            enhanced_item['product_currency'] = product.get('currency')
            break
    else:
        enhanced_item['product_id'] = None
        enhanced_item['matched_name'] = None
    
    return enhanced_item

def get_processing_stats(invoice_data):
    """Get processing statistics"""
    items = invoice_data.get('items', [])
    return {
        'total_items': len(items),
        'matched_items': len([item for item in items if item.get('product_id')]),
        'unmatched_items': len([item for item in items if not item.get('product_id')]),
    }

if __name__ == '__main__':
    os.makedirs('/shared', exist_ok=True)
    
    print("🚀 Starting Simple Invoice Agent Python Service...")
    print("📊 Available endpoints:")
    print("  GET  /health - Health check")
    print("  POST /process-invoice - Basic invoice processing with exact matching")
    
    app.run(host='0.0.0.0', port=5000, debug=True) 