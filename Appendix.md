# Appendix: Gemini Prompts & Python Service

## 1. Gemini Prompts

The node sends the invoice file (as base64) along with a detailed prompts and request JSON payload.

### Request

#### System Prompt

````markdown
You are an intelligent invoice parser. Analyze the provided invoice files.

Your job is to:

1.  Extract key information from the invoice, such as:

    - invoice_number
    - order_date
    - vendor_name
    - shipping_address
    - total_amount
    - currency (e.g., USD, TWD, etc.)
    - payment_method (["Cash", "Bank Transfer", "Credit Card", "Other"])
    - list of items (use the key in English)
      - product_id (品號)
      - product_name (品名)
      - quantity (數量)
      - unit (單位)
      - unit_price (單價)
      - subtotal (小計)
    - tax (if available)

2.  Some of the invoices might be handwritten. Here are some hints for you:

    1.  If the text is in Chinese, please respond in Taiwaness style Traditional Chinese.
    2.  If you find crossed-out items, please ignore them.
    3.  Items are typically written in a format like "{product name} {quantity} {unit}", and there is no price.
    4.  Some of the invoices are long, and items would be in columns.
    5.  Auto-correct the crabbed writing text. For example, units like "兩"(tael) might look like "雨" (rain); we correct it to "兩".
    6.  Some people like to write product names with spaces, for example, a product like "蒜泥" would be written like "蒜 泥". Please do not mistake it as two products, "蒜" and "泥".
    7.  Auto-correct product names. Products are foods and groceries. Please try to provide the correct names.
    8.  Items may look similar, but typically are not repeated.

3.  Return the result in this exact JSON format (We use int for prices):

    ```json
    {
      "invoice_number": "",
      "invoice_date": "YYYY-MM-DD",
      "due_date": "YYYY-MM-DD",
      "vendor_name": "",
      "shipping_address": "",
      "payment_method": "",
      "total_amount": 0,
      "currency": "",
      "tax": 0,
      "items": [
        {
          "product_id": "",
          "product_name": "",
          "quantity": 0,
          "unit": "",
          "unit_price": 0,
          "subtotal": 0
        }
      ]
    }
    ```

4.  If the file isn't a invoice, please return the above JSON format with items list empty.
````

  </details>

#### User Prompt

```markdown
Please extract the invoice data from the given file and only return the required JSON.
```

#### Payload

If you want to update the prompt, you need to convert the prompt to a single line string and paste it into `system_instruction` or `user_prompt` field. You can use the `prompt_converter.html` in `utils/` to do this.

In this payload, I set `thinkingBudget` to 0 to disable the Gemini's thinking.

```json
{
  "system_instruction": {
    "parts": [
      {
        "text": <System Prompt>
      }
    ]
  },
  "contents": [
    {
      "parts": [
        {
          "text": <User Prompt>
        },
        {
          "inline_data": {
            "mime_type": "{{ $json.mime_type }}",
            "data": "{{ $json.data }}"
          }
        }
      ]
    }
  ],
  "generationConfig": {
    "thinkingConfig": {
      "thinkingBudget": 0
    }
  }
}
```

  </details>

### Response

```json
{
  "invoice_data": {
    "invoice_number": "4500567903",
    "invoice_date": "2025-03-29",
    "due_date": "",
    "vendor_name": "家樂福-台北復興",
    "shipping_address": "",
    "payment_method": "Cash",
    "total_amount": 198717,
    "currency": "TWD",
    "tax": 0,
    "items": [
      {
        "product_id": "B059010",
        "product_name": "廣東A/生菜葉",
        "quantity": 15,
        "unit": "斤",
        "unit_price": 189,
        "subtotal": 2835
      },
      ...
    ]
  }
}
```

## 2. Python Service: Product Matching

### APIs

- `GET /health`: A health check endpoint. (Docker Compose will run it automatically.)
- `POST /process-invoice`: Receives invoice JSON data from n8n, performs product matching, and returns the enhanced data.
- `POST /update-alias`: Receives a corrected invoice JSON data and updates the product alias database.

### Request (to `process-invoice` API)

You can use "basic" or "fuzzy" matching method. The default is "fuzzy" (token_set_ratio).

```json
{
  "invoice_data": {{ JSON.stringify($json.invoice_data) }},
  "match_method": "fuzzy"
}
```

### Response (from `process-invoice` API)

- The service returns the processed data with matching statistics.

  ```json
  {
    "processed_data": {
        "currency": "TWD",
        "due_date": "",
        "invoice_date": "2025-03-29",
        "invoice_number": "4500567903",
        "payment_method": "Cash",
        "shipping_address": "",
        "tax": 0,
        "total_amount": 198717,
        "vendor_name": "家樂福-台北復興",
        "items": [
        {
            "match_score": 100,
            "matched_name": "廣東A/生菜葉",
            "original_name": "廣東A/生菜葉",
            "product_id": "B059010",
            "quantity": 15,
            "subtotal": 2835,
            "unit": "KG",
            "unit_price": 189
        },
        ...
        ]
    },
    "processing_stats": {
        "average_match_score": 99.86153846153846,
        "matched_items": 130,
        "max_match_score": 100,
        "min_match_score": 86,
        "total_items": 130,
        "unmatched_items": 0
    },
    // This is the matching time, Gemini's processing time is not included.
    "processing_time": 0.26017093658447266,
    "success": true,
    "timestamp": "2025-06-17T07:23:36.604165"
  }
  ```

- **Possible matches**

  For unmatched items, it may include possible matches, which can be used as a suggestion for the user to manually correct. (However, the current frontend doesn't support this yet because Streamlit dataframe doesn't support dynamic columns.)

  ```json
  {
    "match_score": 67,
    "matched_name": null,
    "original_name": "豬皮",
    "possible_matches": [
      {
        "match_score": 67,
        "matched_name": "肉皮\\豬皮",
        "product_id": "J021010",
        "unit": "斤"
      }
    ],
    "product_id": null,
    "quantity": 8,
    "subtotal": 0,
    "unit": "斤",
    "unit_price": 0
  }
  ```
