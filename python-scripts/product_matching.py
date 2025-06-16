#!/usr/bin/env python3
"""
Simple Invoice processing service with basic product matching
"""

from flask import Flask, request, jsonify
from datetime import datetime, timezone, timedelta
import os
import pandas as pd
from matching_methods import basic_matching, fuzzy_matching, alias_match_item
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
        # Load product database from a fixed path
        try:
            shared_dir = os.path.join(os.path.dirname(__file__), 'shared')
            product_db_path = os.path.join(shared_dir, 'product_db.csv')
            df = pd.read_csv(product_db_path)
            product_db = df.to_dict(orient='records')
        except FileNotFoundError:
            return jsonify({
                "success": False,
                "error": "Product database file not found on the server.",
                "timestamp": datetime.now().isoformat()
            }), 500

        # Load alias database
        alias_db_path = os.path.join(shared_dir, 'product_alias.csv')
        alias_map = {}
        if os.path.exists(alias_db_path):
            print(f"Loading alias database from {alias_db_path}")
            # Load the alias database
            alias_df = pd.read_csv(alias_db_path)
            # Create a map for quick lookups, ensuring keys are lowercase
            # Output: {alias_name: product_id}
            alias_map = {str(k).lower(): v for k, v in pd.Series(alias_df.product_id.values, index=alias_df.alias_name).to_dict().items()}
        else:
            print(f"Alias database not found at {alias_db_path}")

        # Get the invoice data from the request
        data = request.get_json()
        invoice_data = data.get('invoice_data', {})
        match_method = data.get('match_method', 'basic') # Default to basic
        
        # Create a product_id -> product names map for quick lookups
        # Output: {product_id: product_name}
        product_id_map = {p['product_id']: p for p in product_db}

        # Pre-process items with alias matching
        processed_items = []
        items_have_no_alias = []
        for item in invoice_data.get('items', []):
            matched_item = alias_match_item(item, alias_map, product_id_map)
            if matched_item:
                processed_items.append(matched_item)
            else:
                items_have_no_alias.append(item)
        
        # Process remaining items with the selected method
        if items_have_no_alias:
            remaining_invoice_data = invoice_data.copy()
            remaining_invoice_data['items'] = items_have_no_alias
            
            if match_method == 'fuzzy':
                further_processed_data = fuzzy_matching(remaining_invoice_data, product_db)
            else:
                further_processed_data = basic_matching(remaining_invoice_data, product_db)
            
            processed_items.extend(further_processed_data['items'])
        
        # Final processed data
        processed_data = invoice_data.copy()
        processed_data['items'] = processed_items
        
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

@app.route('/update-alias', methods=['POST'])
def update_alias():
    """
    Update the product alias database from a reviewed invoice JSON.
    This endpoint learns from manual corrections.
    """
    data = request.get_json()
    items = data.get('items', [])
    
    if not items:
        return jsonify({"success": False, "message": "No items provided"}), 400
        
    shared_dir = os.path.join(os.path.dirname(__file__), 'shared')
    alias_db_path = os.path.join(shared_dir, 'product_alias.csv')
    
    try:
        if os.path.exists(alias_db_path):
            alias_df = pd.read_csv(alias_db_path)
        else:
            alias_df = pd.DataFrame(columns=['alias_name', 'product_id'])

        new_aliases_count = 0
        for item in items:
            original_name = item.get('original_name')
            product_id = item.get('product_id')
            
            # We consider a match valid for aliasing if product_id is present.
            # The logic is that original_name is an alias for the product
            # identified by product_id.
            if original_name and product_id:
                # Check if the alias already exists and points to the same product_id
                existing_alias = alias_df[alias_df['alias_name'] == original_name]
                if not existing_alias.empty:
                    if existing_alias.iloc[0]['product_id'] != product_id:
                        # Update existing alias if product_id is different
                        alias_df.loc[alias_df['alias_name'] == original_name, 'product_id'] = product_id
                        new_aliases_count += 1
                else:
                    # Add new alias
                    new_alias_df = pd.DataFrame([{'alias_name': original_name, 'product_id': product_id}])
                    alias_df = pd.concat([alias_df, new_alias_df], ignore_index=True)
                    new_aliases_count += 1
        
        if new_aliases_count > 0:
            alias_df.to_csv(alias_db_path, index=False)
        
        return jsonify({
            "success": True, 
            "message": f"Alias database updated. {new_aliases_count} aliases processed."
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

if __name__ == '__main__':
    # Adjust the path to be relative to the script's location
    shared_dir = os.path.join(os.path.dirname(__file__), 'shared')
    os.makedirs(shared_dir, exist_ok=True)
    
    print("🚀 Starting Simple Invoice Agent Python Service...")
    print("📊 Available endpoints:")
    print("  GET  /health - Health check")
    print("  POST /process-invoice - Basic invoice processing with exact matching")
    
    app.run(host='0.0.0.0', port=5000, debug=True) 