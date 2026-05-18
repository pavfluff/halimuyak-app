from flask import Flask, render_template, request, jsonify
import pandas as pd
import requests
import io

app = Flask(__name__)

# get the pricing from google sheet
url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRcjPxbOlxLk02eJyc_KBecdIeG0gOFULpb0dDgfA4zy2vIKyMSZlg5NxTGH1_vaKu3iBxneRSB_xuX/pub?gid=590550743&single=true&output=csv"
def load_base_cost_options(url):
    url = url
    response = requests.get(url)
    df = pd.read_csv(io.StringIO(response.text))
    df.columns = df.columns.str.strip()  # strip whitespace from headers
    return df[["value", "label"]].to_dict(orient="records")

FRAG_COST_OPTIONS = load_base_cost_options(url)

PERFUME_TYPES = {
    "edp": {"name": "Eau de Parfum (EDP)", "min": 15, "max": 25, "default": 20},
    "edt": {"name": "Eau de Toilette (EDT)", "min": 8, "max": 15, "default": 12},
    "edc": {"name": "Eau de Cologne (EDC)", "min": 3, "max": 8, "default": 5},
    "body_splash": {"name": "Body Splash", "min": 2, "max": 4, "default": 3},
    "after_shave": {"name": "After Shave", "min": 1, "max": 3, "default": 2},
}


@app.route("/")
def index():
    return render_template(
        "index.html",
        perfume_types=PERFUME_TYPES,
        base_cost_options=FRAG_COST_OPTIONS
    )


@app.route("/calculate", methods=["POST"])
def calculate():
    try:
        data = request.get_json()
        total_volume = float(data.get("total_volume", 0))
        oil_percentage = float(data.get("oil_percentage", 0))
        perfume_type_key = data.get("perfume_type", "custom")
        oil_cost_per_ml = float(data.get("oil_cost_per_ml", 0) or 0)
        base_cost_per_ml = float(data.get("base_cost_per_ml", 0) or 0)
        bottle_cost = float(data.get("bottle_cost", 0) or 0)

        # Validation
        if total_volume <= 0:
            return jsonify({"error": "Total volume must be greater than 0"}), 400
        if oil_percentage <= 0 or oil_percentage > 100:
            return jsonify({"error": "Oil percentage must be between 0 and 100"}), 400
        if oil_cost_per_ml < 0 or base_cost_per_ml < 0 or bottle_cost < 0:
            return jsonify({"error": "Costs cannot be negative"}), 400

        # Volume calculations
        oil_volume = total_volume * (oil_percentage / 100)
        base_volume = total_volume - oil_volume
        base_percentage = 100 - oil_percentage

        # Cost calculations
        oil_cost = oil_volume * oil_cost_per_ml
        base_cost = base_volume * base_cost_per_ml
        liquid_cost = oil_cost + base_cost
        total_cost = liquid_cost + bottle_cost
        cost_per_ml_output = total_cost / total_volume if total_volume > 0 else 0

        # Perfume type label and warning
        warning = None
        if perfume_type_key in PERFUME_TYPES:
            type_info = PERFUME_TYPES[perfume_type_key]
            perfume_label = type_info["name"]
            if oil_percentage < type_info["min"] or oil_percentage > type_info["max"]:
                warning = (
                    f"Note: {oil_percentage}% is outside the typical "
                    f"{type_info['min']}–{type_info['max']}% range for {type_info['name']}."
                )
        else:
            perfume_label = "Custom Formulation"

        return jsonify({
            "oil_volume": round(oil_volume, 2),
            "base_volume": round(base_volume, 2),
            "base_percentage": round(base_percentage, 2),
            "total_volume": total_volume,
            "oil_percentage": oil_percentage,
            "perfume_label": perfume_label,
            "warning": warning,
            "oil_cost": round(oil_cost, 2),
            "base_cost": round(base_cost, 2),
            "liquid_cost": round(liquid_cost, 2),
            "bottle_cost": round(bottle_cost, 2),
            "total_cost": round(total_cost, 2),
            "cost_per_ml_output": round(cost_per_ml_output, 2),
            "has_costs": oil_cost_per_ml > 0 or base_cost_per_ml > 0 or bottle_cost > 0,
        })

    except (ValueError, TypeError):
        return jsonify({"error": "Please enter valid numbers"}), 400

### for debugging purposes
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
