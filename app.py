import os
import time
import uuid
from flask import Flask, render_template, jsonify, request

app = Flask(__name__)

# Server-Side Authoritative Inventory & Hardware Specs for Noctua Tactical
HARDWARE_CATALOG = {
    "NOCTUA-S315": {
        "sku": "NOCTUA-S315",
        "name": "Noctua S-315 Flagship Monocular",
        "sensor": "384x288 VOx Uncooled Focal Plane",
        "refresh_hz": 50,
        "lens": "15mm Germanium F1.0",
        "detection_range": "1,350 Meters",
        "base_price": 1249.00,
        "stock": 7
    },
    "NOCTUA-G215": {
        "sku": "NOCTUA-G215",
        "name": "Noctua G-215 Recon Monocular",
        "sensor": "256x192 VOx Microbolometer",
        "refresh_hz": 50,
        "lens": "10mm Tactical Wide",
        "detection_range": "780 Meters",
        "base_price": 599.00,
        "stock": 14
    }
}

BUMP_PRICE = 88.00
ORDER_LEDGER = []

@app.route('/')
def home():
    return render_template('index.html', catalog=HARDWARE_CATALOG)

@app.route('/api/telemetry', methods=['GET'])
def get_telemetry():
    """Live server heartbeat & real-time inventory sync for the HUD."""
    return jsonify({
        "status": "ARMED",
        "timestamp": int(time.time()),
        "encryption": "AES-256-GCM // TLS 1.3",
        "node": "NOCTUA-OPS-NODE-01",
        "inventory": {
            k: {"stock": v["stock"], "price": v["base_price"]}
            for k, v in HARDWARE_CATALOG.items()
        }
    })

@app.route('/api/calculate', methods=['POST'])
def calculate_manifest():
    """Server-side price verification so frontend state stays synced with backend."""
    data = request.get_json() or {}
    sku = data.get("sku", "NOCTUA-S315")
    has_bump = bool(data.get("order_bump", False))

    item = HARDWARE_CATALOG.get(sku, HARDWARE_CATALOG["NOCTUA-S315"])
    total = item["base_price"] + (BUMP_PRICE if has_bump else 0.00)

    return jsonify({
        "sku": item["sku"],
        "name": item["name"],
        "sensor": item["sensor"],
        "lens": item["lens"],
        "detection_range": item["detection_range"],
        "has_bump": has_bump,
        "total": round(total, 2),
        "formatted_total": f"${total:,.2f}",
        "stock_remaining": item["stock"]
    })

@app.route('/api/authorize-order', methods=['POST'])
def authorize_order():
    """Receives PayPal capture payload from frontend, decrements stock, returns dispatch manifest."""
    data = request.get_json() or {}
    sku = data.get("sku", "NOCTUA-S315")
    has_bump = bool(data.get("order_bump", False))
    payer_name = data.get("payer_name", "OPERATOR")
    paypal_order_id = data.get("paypal_order_id", "MANUAL-AUTH")

    item = HARDWARE_CATALOG.get(sku, HARDWARE_CATALOG["NOCTUA-S315"])
    if item["stock"] > 0:
        item["stock"] -= 1

    dispatch_hash = f"NC-{uuid.uuid4().hex[:8].upper()}"
    manifest = {
        "dispatch_id": dispatch_hash,
        "paypal_ref": paypal_order_id,
        "operator": payer_name.upper(),
        "hardware": item["name"],
        "emp_case_included": has_bump,
        "total_captured": round(item["base_price"] + (BUMP_PRICE if has_bump else 0.00), 2),
        "remaining_stock": item["stock"],
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
    }
    ORDER_LEDGER.append(manifest)
    return jsonify({"success": True, "manifest": manifest})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)