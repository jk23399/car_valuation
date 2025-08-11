# app/services.py — CIS salePrice (brand+region) + Gemini adjust (Python 3.8+)

import json
import re
import requests
from typing import Optional
from flask import current_app

print(">>> LOADING services:", __file__)

# -----------------------------
# STEP 1) Extract vehicle info from URL (LLM) — EXPANDED
# -----------------------------
def get_vehicle_info_from_url(url: str):
    """
    Return: (raw_string, dict_or_error)
    Uses google.generativeai to extract structured fields needed downstream.
    Fields:
      maker (str), model (str), year (int),
      price (int, listing ask),
      mileage (int, miles), zip (str, 5 digits),
      regionName (str|None, e.g., REGION_STATE_AZ if explicitly present),
      body_type (str in {sedan,suv,pickup,other}),
      condition (str in {excellent,good,fair} — coarsened),
      vin (str|None, 17 chars)
    NOTE:
      - Do NOT invent values. If not present, return null.
      - Strip currency symbols/commas; miles only (no km).
    """
    print("\n--- [STEP 1] get_vehicle_info_from_url (expanded) ---")
    print("URL:", url)

    try:
        # Import here to avoid hard dependency if the lib isn't installed yet
        try:
            import google.generativeai as genai
        except Exception as e:
            return "Import Error", {"error": f"google.generativeai not available: {e}"}

        # Get API key (Gemini or legacy GOOGLE_API_KEY)
        api_key = current_app.config.get("GEMINI_API_KEY") or current_app.config.get("GOOGLE_API_KEY")
        if not api_key:
            return "Configuration Error", {"error": "Google/Gemini API key is not configured."}

        # Fetch raw HTML (use UA to reduce Craigslist bot blocks)
        try:
            resp = requests.get(
                url,
                timeout=20,
                headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome Safari"}
            )
            resp.raise_for_status()
            html_text = resp.text
        except Exception as e:
            return "Fetch Error", {"error": f"Failed to fetch listing HTML: {e}"}

        genai.configure(api_key=api_key)

        # Deterministic-style extraction prompt
        prompt = f"""
You are an information extractor. Work ONLY with the provided HTML/text of a Craigslist car listing.
Return STRICT JSON. Do NOT add commentary or code fences.

Extract:
- maker (string, brand): e.g., "Toyota"
- model (string): e.g., "Camry"
- year (integer, 4-digit)
- price (integer USD ask; remove $ and commas)
- mileage (integer in miles; remove commas; if km is shown, convert to miles by dividing by 1.609 and round)
- zip (5-digit ZIP as string; if multiple, choose the one most closely associated with the listing)
- regionName (string enum if explicitly shown like "REGION_STATE_AZ"; else null)
- body_type (one of: "sedan","suv","pickup","other"; infer from text like 'SUV', 'sedan', 'pickup', 'truck', 'coupe','hatchback'→'other' unless clearly sedan)
- condition (one of: "excellent","good","fair"; map 'like new'/'excellent'→excellent, 'good'/'very good'→good, 'fair'/'needs work'→fair; if absent→good)
- vin (17-char string if present, else null)

Rules:
- Do NOT invent values. If a field is absent, return null.
- Normalize numbers: remove $ and commas; round to nearest integer.
- Prefer explicit numeric fields found near "odometer/mileage".
- Prefer the first plausible 17-char VIN (A-HJ-NPR-Z and digits, no I,O,Q).
- Output strict JSON with keys in this order.

Now parse this content:
<LISTING_HTML>
{html_text}
</LISTING_HTML>

Return ONLY JSON like:
{{
  "maker": "...",
  "model": "...",
  "year": 2018,
  "price": 15499,
  "mileage": 73421,
  "zip": "85281",
  "regionName": null,
  "body_type": "sedan",
  "condition": "good",
  "vin": null
}}
""".strip()

        model = genai.GenerativeModel("gemini-1.5-pro")
        llm = model.generate_content(prompt)

        # Normalize response text
        raw = (getattr(llm, "text", "") or "").strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        if not raw:
            return "Empty LLM", {"error": "LLM returned empty response."}

        # Parse JSON
        data = json.loads(raw)

        # --- Post-parse coercion/sanitization (defensive) ---
        def _to_int(x):
            try:
                return int(round(float(str(x).replace(",", "").replace("$", ""))))
            except Exception:
                return None

        def _zip5(z):
            if not z:
                return None
            s = str(z).strip()
            m = re.search(r"\b(\d{5})\b", s)
            return m.group(1) if m else None

        def _vin17(v):
            if not v:
                return None
            v = str(v).strip().upper()
            if re.match(r"^[A-HJ-NPR-Z0-9]{17}$", v):
                return v
            m = re.search(r"[A-HJ-NPR-Z0-9]{17}", v)
            return m.group(0) if m else None

        def _body(bt, model_name=""):
            bt = (bt or "").lower()
            mn = (model_name or "").lower()
            minivan_models = {
                "odyssey","sienna","caravan","grand caravan","pacifica","sedona","quest",
                "uplander","terraza","freestar","windstar","mpv","mazda5","voyager","precia","previ","precia","pre"
            }
            if "minivan" in bt or any(m in mn for m in minivan_models) or ("van" in bt and "mini" in bt):
                return "minivan"
            if "suv" in bt:
                return "suv"
            if "pickup" in bt or "truck" in bt:
                return "pickup"
            if "sedan" in bt:
                return "sedan"
            return "other"

        def _cond(c):
            c = (c or "").lower()
            if "excellent" in c or "like new" in c:
                return "excellent"
            if "fair" in c or "needs" in c or "project" in c:
                return "fair"
            return "good"

        cleaned = {
            "maker": (data.get("maker") or "").strip(),
            "model": (data.get("model") or "").strip(),
            "year": _to_int(data.get("year")),
            "price": _to_int(data.get("price")),
            "mileage": _to_int(data.get("mileage")),
            "zip": _zip5(data.get("zip")),
            "regionName": (data.get("regionName") or None),
            "body_type": _body(data.get("body_type")),
            "condition": _cond(data.get("condition")),
            "vin": _vin17(data.get("vin")),
            "url": url,
            "body_type": _body(data.get("body_type"), data.get("model"))
        }

        print("[LLM EXTRACTED]", cleaned)
        return raw, cleaned

    except Exception as e:
        print("!!! ERROR get_vehicle_info_from_url:", e)
        return str(e), {"error": f"LLM extraction failed: {e}"}


# -----------------------------
# Helpers
# -----------------------------
def _safe_int(x, default=None):
    try:
        return int(x)
    except Exception:
        try:
            return int(round(float(x)))
        except Exception:
            return default


# -----------------------------
# STEP 2) CIS salePrice baseline (brand + region)
# -----------------------------
def get_saleprice_baseline(brand_name: str, region_name: Optional[str], model_name: Optional[str] = None):
    """
    Calls CIS salePrice and picks the row that best matches model_name.
    If no good match is found, falls back to brand-level aggregate (median of medians).
    """
    print("\n--- [STEP 2] get_saleprice_baseline ---")
    print("brand:", brand_name, "region:", region_name, "model:", model_name)

    cis_key = current_app.config.get("CIS_API_KEY")
    cis_host = current_app.config.get("CIS_HOST", "cis-automotive.p.rapidapi.com")
    if not cis_key:
        return {"error": "CIS_API_KEY not configured."}
    if not brand_name:
        return {"error": "brand_name is required."}

    headers = {"x-rapidapi-key": cis_key, "x-rapidapi-host": cis_host}
    endpoint = f"https://{cis_host}/salePrice"
    params = {"brandName": brand_name}
    if region_name:
        params["regionName"] = region_name

    def _norm(s: str) -> str:
        s = (s or "").lower()
        s = s.replace("-", " ").replace("_", " ")
        return " ".join(s.split())

    def _score(target: str, cand: str) -> int:
        # simple fuzzy score: exact=5, startswith/endswith=4, contains=3, token-overlap=2
        t, c = _norm(target), _norm(cand)
        if not t or not c:
            return 0
        if t == c: return 5
        if c.startswith(t) or c.endswith(t) or t.startswith(c) or t.endswith(c): return 4
        if t in c or c in t: return 3
        # token overlap
        ts, cs = set(t.split()), set(c.split())
        return 2 if (ts & cs) else 0

    try:
        print(f"REQ → {endpoint}  params={params}")
        r = requests.get(endpoint, headers=headers, params=params, timeout=20)
        r.raise_for_status()
        j = r.json()
        print("[RAW]", json.dumps(j, indent=2))

        data = j.get("data")
        base_price = None
        picked_model = None

        # prefer exact/best match if list is returned
        if isinstance(data, list) and model_name:
            best = (-1, None)  # (score, item)
            for it in data:
                name = str(it.get("name", ""))
                sc = _score(model_name, name)
                if sc > best[0]:
                    best = (sc, it)
            if best[0] > 0 and isinstance(best[1], dict):
                it = best[1]
                cand = it.get("median") or it.get("average") or it.get("mean")
                try:
                    base_price = int(round(float(cand)))
                    picked_model = it.get("name")
                except Exception:
                    base_price = None

        # fallback: aggregate brand-level
        if base_price is None and isinstance(data, list):
            vals = []
            for it in data:
                cand = it.get("median") or it.get("average") or it.get("mean")
                try:
                    v = float(cand)
                    if v > 0:
                        vals.append(v)
                except Exception:
                    pass
            if vals:
                vals.sort()
                mid = vals[len(vals)//2] if len(vals) % 2 == 1 else (vals[len(vals)//2-1] + vals[len(vals)//2]) / 2.0
                base_price = int(round(mid))

        if base_price is None and isinstance(data, dict):
            cand = data.get("median") or data.get("average") or data.get("mean")
            try:
                base_price = int(round(float(cand)))
            except Exception:
                base_price = None

        if not base_price or base_price <= 0:
            return {"error": "No usable price stats in salePrice response.", "raw_api_response": j}

        return {"base_price": base_price, "raw_api_response": j, "picked_model": picked_model}

    except requests.exceptions.HTTPError as e:
        print("[ERR] salePrice HTTP:", e)
        return {"error": f"salePrice request failed: {e}"}
    except Exception as e:
        print("[ERR] salePrice unexpected:", e)
        return {"error": f"salePrice unexpected error: {e}"}
    
# -----------------------------
# STEP 3) Gemini adjustment (deterministic)
# -----------------------------
def adjust_price_with_gemini(base_price: int, year: int, mileage: int,
                             body_type: Optional[str], condition: Optional[str],
                             current_year: int):
    # Force local adjustment if configured
    if (current_app.config.get("PRICE_ADJUST_MODE", "local").lower() == "local"):
        body = (body_type or "other").lower()
        condition = (condition or "good").lower()
        return adjust_price_locally(base_price, year, mileage, body, condition, current_year)    
    """
    Deterministic adjustment:
      - Convert new-model baseline to USED baseline with an age-retention curve
      - Apply mileage adjustment with age-dampened cents-per-mile and a cap
    """
    print("\n--- [STEP 3] adjust_price_with_gemini ---")
    print("base(new_model):", base_price, "year:", year, "mileage:", mileage, "body:", body_type, "cond:", condition)

    if not isinstance(base_price, (int, float)) or base_price <= 0:
        return {"error": "Invalid base_price."}
    if not isinstance(year, int) or not isinstance(mileage, int):
        return {"error": "year/mileage must be int."}

    body = (body_type or "other").lower()
    condition = (condition or "good").lower()

    prompt = f"""
You are a calculator. Use ONLY the formula and parameters given. Return strict JSON only.

Inputs:
- new_model_price: {int(base_price)}      # model-specific NEW price baseline
- year: {int(year)}
- mileage: {int(mileage)}
- body_type: "{body}"                     # sedan | suv | pickup | other
- condition: "{condition}"                # excellent | good | fair
- current_year: {int(current_year)}

Fixed params:
- expected_miles_per_year = 12000
- base_cents_per_mile = {{"sedan":0.08,"suv":0.10,"pickup":0.12,"other":0.09}}
- # age retention (price as fraction of new); clamp at 0.15 for >=20 years
- retention_map = {{0:1.00,1:0.80,2:0.70,3:0.62,4:0.56,5:0.51,6:0.47,7:0.44,8:0.41,9:0.38,10:0.35,11:0.32,12:0.30,13:0.28,14:0.26,15:0.24,16:0.22,17:0.20,18:0.18,19:0.16,20:0.15}}
- condition_factor = {{"excellent":1.02,"good":1.00,"fair":0.97}}

Steps:
1) age = max(0, current_year - year)
2) r = retention_map[min(age, 20)]
3) used_base = new_model_price * r
4) expected_miles = min(age, 15) * expected_miles_per_year   # cap horizon for mileage expectation
5) delta_miles = mileage - expected_miles
6) cppm = base_cents_per_mile.get(body_type, 0.09)
7) cppm_age = max(0.02, cppm * max(0.3, 1 - 0.06*age))       # dampen with age
8) raw_mileage_adj = - cppm_age * delta_miles
9) cap = 0.35 * used_base                                     # cap mileage effect to ±35% of used_base
10) mileage_adj = max(-cap, min(raw_mileage_adj, cap))
11) fair = max(0, used_base + mileage_adj) * condition_factor[condition]
12) low = fair * 0.95; high = fair * 1.05

Return strict JSON:
{{"fair": <int>, "low": <int>, "high": <int>, "age": <int>, "retention": <float>, "used_base": <int>, "delta_miles": <int>, "mileage_adj": <int>}}
""".strip()

    try:
        import google.generativeai as genai
        gemini_key = current_app.config.get("GEMINI_API_KEY") or current_app.config.get("GOOGLE_API_KEY")
        if not gemini_key:
            raise RuntimeError("Gemini API key not configured.")
        genai.configure(api_key=gemini_key)
        model = genai.GenerativeModel("gemini-1.5-flash")
        resp = model.generate_content(prompt)
        text = (resp.text or "").strip().replace("```json", "").replace("```", "").strip()
        j = json.loads(text)
        # force ints where appropriate
        for k in ["fair","low","high","used_base","delta_miles","mileage_adj","age"]:
            if k in j and isinstance(j[k], float):
                j[k] = int(round(j[k]))
        return j
    except Exception as e:
        print("[WARN] Gemini failed, using local formula:", e)
        return adjust_price_locally(base_price, year, mileage, body, condition, current_year)


def adjust_price_locally(base_price: int, year: int, mileage: int,
                         body_type: str, condition: str, current_year: int):
    """Deterministic local fallback; reads tunables from Flask config."""
    cfg = current_app.config

    expected_miles_per_year = int(cfg.get("PRICE_EXPECTED_MILES_PER_YEAR", 12000))
    cpm_map = cfg.get("PRICE_CPM_MAP") or {"sedan":0.08,"suv":0.10,"pickup":0.12,"minivan":0.09,"other":0.09}
    retention_map = cfg.get("PRICE_RETENTION_MAP") or {
        0:1.00,1:0.80,2:0.70,3:0.62,4:0.56,5:0.51,6:0.47,7:0.44,8:0.41,9:0.38,
        10:0.34,11:0.31,12:0.28,13:0.26,14:0.24,15:0.22,16:0.20,17:0.18,18:0.16,19:0.14,20:0.13
    }
    # normalize retention_map keys to int
    retention_map = {int(k): float(v) for (k, v) in retention_map.items()}
    mileage_cap_frac = float(cfg.get("PRICE_MILEAGE_CAP", 0.35))

    condition_factor = {"excellent":1.02,"good":1.00,"fair":0.97}

    age = max(0, current_year - int(year))
    r = retention_map[20 if age > 20 else age]
    used_base = base_price * r

    # age-dampened mileage effect with cap
    expected_miles = min(age, 15) * expected_miles_per_year
    delta_miles = int(mileage) - expected_miles
    cppm = cpm_map.get(body_type, cpm_map.get("other", 0.09))
    cppm_age = max(0.02, cppm * max(0.3, 1 - 0.06 * age))
    raw_mileage_adj = - cppm_age * delta_miles
    cap = mileage_cap_frac * used_base
    mileage_adj = max(-cap, min(raw_mileage_adj, cap))

    fair = max(0, used_base + mileage_adj) * condition_factor.get(condition, 1.0)
    low, high = fair * 0.95, fair * 1.05

    print(f"[LOCAL] age={age}, r={r:.2f}, used_base={used_base:.0f}, delta={delta_miles}, "
          f"cppm={cppm:.3f}->{cppm_age:.3f}, adj={mileage_adj:.0f}, cap={cap:.0f}, fair={fair:.0f}")

    return {
        "fair": int(round(fair)),
        "low": int(round(low)),
        "high": int(round(high)),
        "age": int(age),
        "retention": float(r),
        "used_base": int(round(used_base)),
        "delta_miles": int(delta_miles),
        "mileage_adj": int(round(mileage_adj)),
    }
    
# -----------------------------
# STEP 4) Orchestrator
# -----------------------------
def get_valuation(vehicle_data: dict) -> dict:
    """
    Orchestrates: CIS salePrice (brand+region) -> Gemini adjustment -> final valuation.
    Requires at least: maker (brand), year (int), mileage (int).
    Optional: regionName, body_type, condition.
    """
    print("\n--- [STEP 4] get_valuation ---")
    print("vehicle_data:", vehicle_data)

    mode = current_app.config.get("API_MODE", "real")
    if mode == "mock":
        price = vehicle_data.get("price", 0)
        return {
            "valuation_price": int(price * 1.08) if isinstance(price, (int, float)) else 0,
            "source": "Mock"
        }

    maker = (vehicle_data.get("maker") or vehicle_data.get("make") or "").strip()
    model_name = (vehicle_data.get("model") or vehicle_data.get("modelName") or "").strip()
    year = _safe_int(vehicle_data.get("year"))
    mileage = _safe_int(vehicle_data.get("mileage"))
    if not maker or year is None or mileage is None:
        return {"error": "maker/year/mileage are required for valuation."}

    region_name = vehicle_data.get("regionName") or current_app.config.get("DEFAULT_REGION")
    body_type = vehicle_data.get("body_type")
    condition = vehicle_data.get("condition")

    # 1) CIS baseline
    base = get_saleprice_baseline(                                          # ← pass model_name
        brand_name=maker,
        region_name=region_name,
        model_name=model_name
    )

    base_price = base.get("base_price")
    if not base_price:
        return {"error": "Could not determine base_price from salePrice response.", "raw": base.get("raw_api_response")}

    # 2) Adjustment
    current_year = int(current_app.config.get("CURRENT_YEAR", 2025))
    adj = adjust_price_with_gemini(
        base_price=base_price,
        year=year,
        mileage=mileage,
        body_type=body_type,
        condition=condition,
        current_year=current_year
    )
    if adj.get("error"):
        return {"error": adj["error"]}

    # 3) Final payload
    valuation_price = adj.get("fair")
    return {
        "valuation_price": valuation_price,
        "range": {"low": adj.get("low"), "high": adj.get("high")},
        "adjust_detail": {
            "age": adj.get("age"),
            "retention": adj.get("retention"),
            "used_base": adj.get("used_base"),
            "delta_miles": adj.get("delta_miles"),
            "mileage_adj": adj.get("mileage_adj"),
            "base_price": base_price,
            "picked_model": base.get("picked_model"),
            "regionName": region_name,
            "brandName": maker
        },
        "source": "CIS salePrice (model row) + age/mileage adjust"
    }


# -----------------------------
# STEP 5) Deal rating
# -----------------------------
def calculate_deal_rating(listing_price: int, valuation_price: int) -> dict:
    if not isinstance(listing_price, (int, float)) or not isinstance(valuation_price, (int, float)) or valuation_price == 0:
        return {"rating": "N/A", "comment": "Could not determine valuation due to missing price data."}

    diff = valuation_price - listing_price
    pct = (diff / valuation_price) * 100

    if pct > 10:
        rating = "Excellent Deal"
    elif pct > 3:
        rating = "Good Deal"
    elif pct > -5:
        rating = "Fair Price"
    else:
        rating = "Overpriced"

    price_diff_str = f"${abs(diff):,}"
    market_value_str = f"${valuation_price:,}"

    if rating == "Fair Price":
        comment = f"This car's price is close to our estimated market value of {market_value_str}."
    else:
        comparison = "below" if diff > 0 else "above"
        comment = f"This car is listed {price_diff_str} (≈{abs(pct):.1f}%) {comparison} our estimated market value of {market_value_str}."

    return {"rating": rating, "comment": comment}

# --- Risk flags analyzer ---
def analyze_flags(vehicle_data: dict) -> list:
    """
    Emit risk flags based on extracted listing info.
    Currently: red flag if VIN is missing or invalid.
    """
    flags = []
    vin = (vehicle_data.get("vin") or "").strip()
    if len(vin) != 17:
        flags.append({
            "code": "VIN_MISSING",
            "level": "red",
            "label": "Red flag",
            "message": "VIN not shown in the listing. Ask the seller for a VIN photo (windshield/driver-door sticker) before meeting."
        })
    return flags

# Explicit export list (helps avoid attribute confusion)
__all__ = [
    "get_vehicle_info_from_url",
    "get_saleprice_baseline",
    "adjust_price_with_gemini",
    "adjust_price_locally",
    "get_valuation",
    "calculate_deal_rating",
    "analyze_flags",
]
