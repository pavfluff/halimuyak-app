from flask import Flask, render_template, request, jsonify
import pandas as pd
import requests
import io
import random
import string
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import os
import json
import base64

app = Flask(__name__)

credentials_json = base64.b64decode(
    os.environ["GOOGLE_CREDENTIALS_BASE64"]
).decode("utf-8")

credentials_dict = json.loads(credentials_json)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

credentials = Credentials.from_service_account_info(
    credentials_dict,
    scopes=SCOPES
)

# credentials = Credentials.from_service_account_info({
#     "type": "service_account",
#     "project_id": os.environ["GOOGLE_PROJECT_ID"],
#     "private_key_id": os.environ["GOOGLE_PRIVATE_KEY_ID"],
#     "private_key": os.environ["GOOGLE_PRIVATE_KEY"].replace("\\n", "\n"),
#     "client_email": os.environ["GOOGLE_CLIENT_EMAIL"],
#     "client_id": os.environ["GOOGLE_CLIENT_ID"],
#     "token_uri": "https://oauth2.googleapis.com/token",
# }, scopes=SCOPES)

# ── Google Sheet config ───────────────────────────────────────────────────────
CREDENTIALS_FILE = "halimuyak.json"          # ← path to your service account JSON
SHEET_ID         = "1l_PT8imyyLRGU3yD0-Td6kHn7h52MxDmHItYb9UNzq0" # ← the long ID from your sheet URL
ORDERS_TAB       = "Orders - Auto"           # ← exact tab name

def get_orders_sheet():
    """Return the gspread worksheet for orders."""
    # creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
    creds = credentials
    gc    = gspread.authorize(creds)
    sh    = gc.open_by_key(SHEET_ID)
    return sh.worksheet(ORDERS_TAB)

# ── Fragrance oil pricing CSV URL ─────────────────────────────────────────────
PRICING_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRcjPxbOlxLk02eJyc_KBecdIeG0gOFULpb0dDgfA4zy2vIKyMSZlg5NxTGH1_vaKu3iBxneRSB_xuX/pub?gid=590550743&single=true&output=csv"

def load_base_cost_options(url):
    response = requests.get(url)
    df = pd.read_csv(io.StringIO(response.text))
    df.columns = df.columns.str.strip()
    if "image_url" in df.columns:
        df["image_url"] = df["image_url"].fillna("")
    else:
        df["image_url"] = ""
    return df[["value", "label", "image_url"]].to_dict(orient="records")

FRAG_COST_OPTIONS = load_base_cost_options(PRICING_URL)

PERFUME_TYPES = {
    "edp":         {"name": "Eau de Parfum (EDP)",  "min": 15, "max": 25, "default": 20},
    "edt":         {"name": "Eau de Toilette (EDT)", "min": 8,  "max": 15, "default": 12},
    "edc":         {"name": "Eau de Cologne (EDC)",  "min": 3,  "max": 8,  "default": 5},
    "body_splash": {"name": "Body Splash",           "min": 2,  "max": 4,  "default": 3},
    "after_shave": {"name": "After Shave",           "min": 1,  "max": 3,  "default": 2},
}


def generate_order_id(existing_ids):
    """Generate a unique HLM-XXXX order ID."""
    while True:
        suffix   = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        order_id = f"HLM-{suffix}"
        if order_id not in existing_ids:
            return order_id


@app.route("/")
def index():
    return render_template("index.html", perfume_types=PERFUME_TYPES, base_cost_options=FRAG_COST_OPTIONS)


@app.route("/calculate", methods=["POST"])
def calculate():
    try:
        data             = request.get_json()
        total_volume     = float(data.get("total_volume", 0))
        oil_percentage   = float(data.get("oil_percentage", 0))
        perfume_type_key = data.get("perfume_type", "custom")
        oil_cost_per_ml  = float(data.get("oil_cost_per_ml", 0) or 0)
        base_cost_per_ml = float(data.get("base_cost_per_ml", 0) or 0)
        bottle_cost      = float(data.get("bottle_cost", 0) or 0)
        crochet_cost     = float(data.get("crochet_cost", 0) or 0)

        if total_volume <= 0:
            return jsonify({"error": "Total volume must be greater than 0"}), 400
        if oil_percentage <= 0 or oil_percentage > 100:
            return jsonify({"error": "Oil percentage must be between 0 and 100"}), 400
        if any(x < 0 for x in [oil_cost_per_ml, base_cost_per_ml, bottle_cost, crochet_cost]):
            return jsonify({"error": "Costs cannot be negative"}), 400

        oil_volume      = total_volume * (oil_percentage / 100)
        base_volume     = total_volume - oil_volume
        base_percentage = 100 - oil_percentage
        oil_cost        = oil_volume * oil_cost_per_ml
        base_cost       = base_volume * base_cost_per_ml
        liquid_cost     = oil_cost + base_cost
        total_cost      = liquid_cost + bottle_cost + crochet_cost
        cost_per_ml_out = total_cost / total_volume if total_volume > 0 else 0

        warning = None
        if perfume_type_key in PERFUME_TYPES:
            ti            = PERFUME_TYPES[perfume_type_key]
            perfume_label = ti["name"]
            if oil_percentage < ti["min"] or oil_percentage > ti["max"]:
                warning = (f"Note: {oil_percentage}% is outside the typical "
                           f"{ti['min']}–{ti['max']}% range for {ti['name']}.")
        else:
            perfume_label = "Custom Formulation"

        return jsonify({
            "oil_volume":         round(oil_volume, 2),
            "base_volume":        round(base_volume, 2),
            "base_percentage":    round(base_percentage, 2),
            "total_volume":       total_volume,
            "oil_percentage":     oil_percentage,
            "perfume_label":      perfume_label,
            "warning":            warning,
            "oil_cost":           round(oil_cost, 2),
            "base_cost":          round(base_cost, 2),
            "liquid_cost":        round(liquid_cost, 2),
            "bottle_cost":        round(bottle_cost, 2),
            "crochet_cost":       round(crochet_cost, 2),
            "total_cost":         round(total_cost, 2),
            "cost_per_ml_output": round(cost_per_ml_out, 2),
            "has_costs": oil_cost_per_ml > 0 or base_cost_per_ml > 0 or bottle_cost > 0,
        })

    except (ValueError, TypeError):
        return jsonify({"error": "Please enter valid numbers"}), 400


@app.route("/place_order", methods=["POST"])
def place_order():
    try:
        data = request.get_json()

        ws = get_orders_sheet()

        # ── Get existing Order IDs to avoid collisions ────────────────────
        all_values   = ws.get_all_values()
        existing_ids = {row[0] for row in all_values[1:] if row}  # skip header
        order_id     = generate_order_id(existing_ids)

        order_date    = datetime.now().strftime("%m/%d/%Y")
        customer_name = data.get("customer_name", "").strip() or "—"
        ordered_thru  = data.get("ordered_through", "Aging")
        total_volume  = data.get("total_volume", "")
        frag_oil_name = data.get("frag_oil_name", "")
        croc_cost     = data.get("crochet_cost", 0)
        frag_oil_vol  = data.get("oil_volume", "")
        bottle_label  = data.get("bottle_label", "")
        total_cost    = data.get("total_cost", "")
        oil_pct       = data.get("oil_percentage", "")

        row = [
            order_id,
            order_date,
            customer_name,
            ordered_thru,
            total_volume,
            frag_oil_name,
            croc_cost if float(croc_cost or 0) > 0 else "",
            frag_oil_vol,
            oil_pct,
            bottle_label,
            total_cost,
            "Pending",
            ""              # Comment
        ]

        ws.append_row(row, value_input_option="USER_ENTERED")

        return jsonify({"success": True, "order_id": order_id, "customer_name": customer_name})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
