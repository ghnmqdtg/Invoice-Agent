import streamlit as st
import pandas as pd
import json
import requests
import os
from datetime import datetime

st.set_page_config(layout="wide")

st.title("Invoice Product Matching Assistant")

st.info("""
**Workflow:**
1. Upload your invoice file (PDF, PNG, or JPG).
2. Click "Process Invoice" to have AI extract and match the products.
3. Correct any uncertain matches in the table below.
""")

# --- Load Product Database from a fixed path ---
@st.cache_data
def load_product_db():
    # Path relative to the script location
    script_dir = os.path.dirname(__file__)
    db_path = os.path.join(script_dir, "shared", "product_db.csv")
    try:
        df = pd.read_csv(db_path)
        return df.to_dict(orient='records')
    except FileNotFoundError:
        st.error(f"Error: Product database not found at `{db_path}`. Please ensure the file exists.")
        return None

product_db = load_product_db()
if product_db:
    st.session_state.product_db = product_db

# --- File Uploads ---
st.header("Upload Invoice")
invoice_file = st.file_uploader(
    "Upload your invoice", type=["pdf", "png", "jpg", "jpeg"]
)

if invoice_file:
    st.write(f"Uploaded file: `{invoice_file.name}`")
    if st.button("Process Invoice"):
        n8n_webhook_url = "http://localhost:8080/webhook-test/e77b5a73-f0ef-42ff-9519-8e5bbb7d7af4"
        
        files = {"file": (invoice_file.name, invoice_file.getvalue(), invoice_file.type)}
        with st.spinner("Processing invoice via n8n... This may take a moment."):
            try:
                response = requests.post(n8n_webhook_url, files=files, timeout=300)
                response.raise_for_status()
                
                processed_json = response.json()
                
                # The python service nests the data in a 'processed_data' key.
                # We extract it here. If not found, we assume the whole response is the data.
                st.session_state.processed_data = processed_json.get('processed_data', processed_json)
                
                st.success("Invoice processed! Please review the matches below.")
            except requests.exceptions.RequestException as e:
                st.error(f"Failed to process invoice: {e}")
                # Try to show more helpful error from response
                try:
                    st.error(f"Response content: {response.text}")
                except NameError:
                    pass # response object may not exist

if 'processed_data' in st.session_state:
    st.header("Invoice Summary")
    st.write("You can edit the invoice summary details here if anything is missing or incorrect.")
    invoice_data = st.session_state.processed_data
    
    col1, col2 = st.columns(2)

    with col1:
        vendor_name = st.text_input(
            "Vendor Name",
            value=invoice_data.get("vendor_name") or ""
        )
        
        # --- Date Picker for Invoice Date ---
        current_date_val = None
        date_str = invoice_data.get("invoice_date")
        if date_str:
            try:
                # Use pandas to parse various date formats robustly
                current_date_val = pd.to_datetime(date_str).date()
            except (ValueError, TypeError):
                st.warning(f"Could not automatically parse date: '{date_str}'. Please select it manually.")
                current_date_val = None

        invoice_date = st.date_input(
            "Invoice Date",
            value=current_date_val,
            format="YYYY-MM-DD"
        )

    with col2:
        invoice_number = st.text_input(
            "Invoice Number",
            value=invoice_data.get("invoice_number") or ""
        )
        
        sub_col1, sub_col2 = st.columns(2)
        with sub_col1:
            try:
                current_total = int(invoice_data.get("total_amount", 0))
            except (ValueError, TypeError):
                current_total = 0
            total_amount = st.number_input(
                "Total Amount",
                value=current_total,
                step=1,
                format="%d"
            )
        with sub_col2:
            currency = st.text_input(
                "Currency",
                value=invoice_data.get("currency") or ""
            )

    # Update the session state with the potentially modified values
    st.session_state.processed_data['vendor_name'] = vendor_name
    st.session_state.processed_data['invoice_date'] = invoice_date.strftime('%Y-%m-%d') if invoice_date else None
    st.session_state.processed_data['invoice_number'] = invoice_number
    st.session_state.processed_data['total_amount'] = total_amount
    st.session_state.processed_data['currency'] = currency

    st.header("Processed Items")
    st.write("Below are all items extracted from the invoice. You can directly edit the matched product in the table. Items requiring your attention are highlighted.")

    if 'items' in invoice_data and invoice_data['items']:
        # Prepare data for the table on first run
        if 'edited_df' not in st.session_state:
            table_data = []
            for item in invoice_data['items']:
                item_copy = item.copy()
                if item_copy.get('product_id') is None:
                    item_copy['status'] = 'Review Required'
                else:
                    item_copy['status'] = 'Matched'
                table_data.append(item_copy)
            df = pd.DataFrame(table_data)
            # The 'possible_matches' column can contain mixed types (lists of dicts, empty lists)
            # which Arrow cannot serialize. We can safely drop it as it's not used in the UI.
            if 'possible_matches' in df.columns:
                df = df.drop(columns=['possible_matches'])
            st.session_state.edited_df = df

        # --- In-place Table Editing ---

        # 1. Prepare product list for dropdown
        all_products = st.session_state.get('product_db', [])
        product_names = [p['product_name'] for p in all_products if p.get('product_name')]
        product_db_map = {p['product_name']: p for p in all_products}

        # Styler function to highlight rows
        def highlight_review_rows(row):
            color = '#FFF3CD' if row.status == 'Review Required' else ''
            return [f'background-color: {color}' for _ in row]
        
        # Keep a copy of the dataframe before editing
        df_before_edit = st.session_state.edited_df.copy()

        # Define columns to display and their order
        display_cols = [
            'status', 'product_id', 'original_name', 'matched_name', 'quantity',
            'unit', 'unit_price', 'subtotal'
        ]
        
        # Ensure all display columns exist in the dataframe before passing to column_order
        existing_display_cols = [col for col in display_cols if col in st.session_state.edited_df.columns]

        edited_df = st.data_editor(
            st.session_state.edited_df.style.apply(highlight_review_rows, axis=1),
            column_config={
                "status": st.column_config.TextColumn("Status", disabled=True),
                "product_id": st.column_config.TextColumn("Product ID", disabled=True),
                "original_name": st.column_config.TextColumn("Original Name", disabled=True),
                "matched_name": st.column_config.SelectboxColumn(
                    "Matched Product",
                    help="Select the correct product from the database.",
                    options=sorted(product_names),
                    required=False,
                ),
                "quantity": st.column_config.NumberColumn("Quantity", format="%d"),
                "unit": st.column_config.TextColumn("Unit", disabled=True),
                "unit_price": st.column_config.NumberColumn("Unit Price", format="%d", disabled=True),
                "subtotal": st.column_config.NumberColumn("Subtotal", format="%d", disabled=True),
                "match_score": None, # Hide match_score column
            },
            use_container_width=True,
            hide_index=False,
            column_order=existing_display_cols,
            num_rows="dynamic", # Allow adding/deleting rows
            key="product_editor"
        )
        
        # Detect changes and update dependent columns
        if not edited_df.equals(df_before_edit):
            # On any change, re-process the entire dataframe to update derived values
            for i in edited_df.index:
                selected_product_name = edited_df.loc[i, 'matched_name']
                
                if pd.isna(selected_product_name) or selected_product_name is None:
                    # Product deselected or it's a new empty row
                    edited_df.loc[i, 'product_id'] = None
                    edited_df.loc[i, 'status'] = 'Review Required'
                    # For new rows, some fields will be NaN. Let's not set them to 0 yet.
                    is_new_row = i not in df_before_edit.index
                    if is_new_row:
                        edited_df.loc[i, 'unit'] = None
                        edited_df.loc[i, 'unit_price'] = 0.0
                else:
                    # A product is selected, so update its details from the DB
                    selected_product_details = product_db_map.get(selected_product_name, {})
                    edited_df.loc[i, 'product_id'] = selected_product_details.get('product_id')
                    edited_df.loc[i, 'unit'] = selected_product_details.get('unit')
                    # Assume product_db might have unit_price
                    unit_price = selected_product_details.get('unit_price', 0.0)
                    edited_df.loc[i, 'unit_price'] = unit_price
                    edited_df.loc[i, 'status'] = 'Matched'

                # Always recalculate subtotal
                quantity = edited_df.loc[i, 'quantity']
                unit_price = edited_df.loc[i, 'unit_price']
                if pd.notna(quantity) and pd.notna(unit_price):
                    edited_df.loc[i, 'subtotal'] = float(quantity) * float(unit_price)
                else:
                    edited_df.loc[i, 'subtotal'] = 0.0

            st.session_state.edited_df = edited_df
            st.rerun()

    else:
        st.info("No items were extracted from the invoice.")

    if st.button("Finalize and Generate JSON"):
        final_data = st.session_state.processed_data.copy()
        
        # Use the final state of the dataframe from session state
        final_items_df = st.session_state.edited_df.copy()
        
        # Convert dataframe to a list of dicts for the final JSON
        final_items = final_items_df.to_dict(orient='records')

        # Clean up NaN values for JSON serialization and add other final details
        cleaned_final_items = []
        for item in final_items:
            # Skip empty rows that might have been added but not filled
            if pd.isna(item.get('original_name')) and pd.isna(item.get('matched_name')):
                continue

            cleaned_item = {}
            for key, value in item.items():
                # Replace pandas NaN with None for valid JSON
                cleaned_item[key] = None if pd.isna(value) else value
            
            # Ensure required fields exist even for new rows
            cleaned_item.setdefault('original_name', cleaned_item.get('matched_name'))

            if cleaned_item.get('matched_name'):
                selection = product_db_map.get(cleaned_item['matched_name'], {})
                cleaned_item['match_score'] = 100
            else:
                cleaned_item['match_score'] = 0
            
            cleaned_item.pop('status', None) # Remove temporary UI field
            cleaned_final_items.append(cleaned_item)

        final_data['items'] = cleaned_final_items
        
        # Recalculate the grand total based on the final list of items
        final_data['total_amount'] = sum(
            item.get('subtotal', 0) or 0 for item in cleaned_final_items
        )
        
        st.session_state.final_data = final_data
        st.rerun()

if 'final_data' in st.session_state:
    st.header("Completed JSON")
    st.json(st.session_state.final_data)
    file_name = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_invoice_{st.session_state.final_data['invoice_number']}.json"
    # Add file_name to the final data
    st.session_state.final_data['file_name'] = file_name
    # Remove `processed_at` in the final data
    st.session_state.final_data.pop('processed_at', None)
    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            label="Download Final JSON",
            data=json.dumps(st.session_state.final_data, indent=2),
            # Use datetime as the file name
            file_name=file_name,
            mime="application/json"
        )
    with col2:
        if st.button("Upload to database"):
            n8n_gdrive_webhook_url = "http://localhost:8080/webhook-test/9e7c8a70-275e-49d7-9bae-a478660d5aef"
            
            with st.spinner("Uploading to database via n8n..."):
                try:
                    headers = {'Content-Type': 'application/json'}
                    response = requests.post(
                        n8n_gdrive_webhook_url,
                        data=json.dumps(st.session_state.final_data),
                        headers=headers,
                        timeout=60
                    )
                    response.raise_for_status()
                    # If the response is 200, then the file is uploaded to the database
                    if response.status_code == 200:
                        st.success("Successfully uploaded to the database!")
                    else:
                        st.error(f"Failed to upload to database: {response.text}")
                except requests.exceptions.RequestException as e:
                    st.error(f"Failed to upload to database: {e}")
                    try:
                        st.error(f"Response content: {response.text}")
                    except NameError:
                        pass # response object may not exist

    if st.button("Upload the next file"):
        # Clear the session state to allow for a new upload, preserving the product DB
        for key in list(st.session_state.keys()):
            if key != 'product_db':
                del st.session_state[key]
        st.rerun() 
