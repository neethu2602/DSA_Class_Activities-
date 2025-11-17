from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.db.models import Sum, Avg
from django.conf import settings

import os
import joblib
import pandas as pd

from .forms import FarmerRegisterForm
from .models import MilkRecord

# ============================================================
# 🏠 HOME PAGE
# ============================================================

def home(request):
    return render(request, 'home.html')


# ============================================================
# 🔐 AUTHENTICATION VIEWS
# ============================================================

def login_view(request):
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f"Welcome back, {user.username}!")
            return redirect('dashboard')
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = AuthenticationForm()
    return render(request, 'login.html', {'form': form})



def register_view(request):
    """User registration view"""
    if request.method == "POST":
        form = FarmerRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"Account created for {user.username}!")
            return redirect('dashboard')
        else:
            messages.error(request, "Registration failed. Please check the form.")
    else:
        form = FarmerRegisterForm()
    return render(request, 'register.html', {'form': form})


def logout_view(request):
    """User logout view"""
    logout(request)
    messages.success(request, "Logged out successfully!")
    return redirect('home')


# ============================================================
# 🥛 MILK RATE CALCULATION
# ============================================================

def calculate_rate(fat, snf):
    """Simple milk rate calculation"""
    try:
        return round(fat * 2 + snf * 1.5, 2)
    except Exception:
        return 0.0


# ============================================================
# 🟢 DASHBOARD VIEW
# ============================================================


@login_required
def dashboard(request):
    records = MilkRecord.objects.filter(farmer=request.user).order_by('-date')

    # Auto-calculate rate if missing
    for r in records:
        if not hasattr(r, 'rate') or r.rate is None:
            r.rate = calculate_rate(r.fat_content, r.snf)
            r.save()

    total_milk = records.aggregate(Sum('quantity'))['quantity__sum'] or 0
    avg_rate = records.aggregate(Avg('rate'))['rate__avg'] or 0
    last_date = records.first().date if records.exists() else None
    total_records = records.count()

    # Pass the cards as context
    cards = [
        {'icon':'fa-bottle-droplet','title':'Total Milk (L)','value':total_milk,'color':'success'},
        {'icon':'fa-indian-rupee-sign','title':'Average Rate','value':'₹'+str(round(avg_rate,2)),'color':'warning'},
        {'icon':'fa-calendar-day','title':'Last Supply','value':last_date,'color':'primary'},
        {'icon':'fa-clipboard-list','title':'Total Records','value':total_records,'color':'danger'},
    ]

    context = {
        'records': records,
        'cards': cards,
    }
    return render(request, 'dashboard.html', context)



# ============================================================
# 📦 LOAD ML MODELS
# ============================================================

import os
import joblib
from django.conf import settings

MODEL_DIR = os.path.join(settings.BASE_DIR, "milkapp", "ml_models")
PRICE_MODEL_FN = os.path.join(MODEL_DIR, "best_price_model_RandomForest.pkl")
BREED_MODEL_FN = os.path.join(MODEL_DIR, "breed_pipe.pkl")
QUALITY_MODEL_FN = os.path.join(MODEL_DIR, "quality_kmeans_model.pkl")


def safe_load_model(path):
    """Safely load joblib model and handle missing/corrupt cases."""
    try:
        model = joblib.load(path)
        print(f"✅ Loaded model: {os.path.basename(path)}")
        return model
    except Exception as e:
        print(f"⚠️ Could not load {path}: {e}")
        return None


price_pipe = safe_load_model(PRICE_MODEL_FN)
breed_pipe = safe_load_model(BREED_MODEL_FN)
quality_kmeans = safe_load_model(QUALITY_MODEL_FN)

print("✅ Model load summary:")
print(" - Price model:", "Loaded ✅" if price_pipe else "❌ Missing")
print(" - Breed model:", "Loaded ✅" if breed_pipe else "❌ Missing")
print(" - Quality model:", "Loaded ✅" if quality_kmeans else "❌ Missing")



# ============================================================
# 💰 PRICE PREDICTION
# ============================================================

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
import pandas as pd
import traceback

@login_required
def predict_price(request):
    result, error = None, None
    fat = snf = clr = litre = quality_code = ""
    rainfall = temperature = humidity = ""

    try:
        if request.method == "POST":
            fat = float(request.POST.get("fat"))
            snf = float(request.POST.get("snf"))
            clr = float(request.POST.get("clr") or 0)
            litre = float(request.POST.get("litre") or 1)
            quality_code = request.POST.get("quality_code") or "B"
            rainfall = float(request.POST.get("rainfall_mm"))
            temperature = float(request.POST.get("temperature_c"))
            humidity = float(request.POST.get("humidity_percent"))

            quality_map = {'A': 3, 'B': 2, 'C': 1}
            quality_value = quality_map.get(quality_code, 2)

            X = pd.DataFrame([{
                "FAT": fat,
                "SNF": snf,
                "CLR": clr,
                "Rainfall_mm": rainfall,
                "Temperature_C": temperature,
                "Humidity_%": humidity,
                "LITRE": litre,
                "Quality_Code": quality_value
            }])

            print("🔹 Input for Price Prediction:\n", X)

            if price_pipe is not None:
                pred_price = price_pipe.predict(X)[0]
                result = round(float(pred_price), 2)
                print("✅ Predicted Price:", result)
            else:
                error = "Price model not loaded."

        else:  # GET request
            fat = request.GET.get("fat", "")
            snf = request.GET.get("snf", "")
            clr = request.GET.get("clr", "")
            quality_code = request.GET.get("quality_code", "")
            rainfall = request.GET.get("rainfall_mm", "")
            temperature = request.GET.get("temperature_c", "")
            humidity = request.GET.get("humidity_percent", "")
            litre = request.GET.get("litre", 1)

    except Exception as e:
        import traceback
        traceback.print_exc()
        error = f"Error during prediction: {str(e)}"

    return render(request, "predict_price.html", {
        "result": result,
        "error": error,
        "fat": fat,
        "snf": snf,
        "clr": clr,
        "litre": litre,
        "quality_code": quality_code,
        "rainfall_mm": rainfall,
        "temperature_c": temperature,
        "humidity_percent": humidity
    })





@login_required
def predict_quality(request):
    result, error = None, None
    fat = snf = clr = rainfall = temperature = humidity = ""

    if quality_kmeans is None:
        error = "Quality model not loaded."
    else:
        try:
            # Use POST if form submitted, else GET for prefill
            fat = request.POST.get("fat", request.GET.get("fat", ""))
            snf = request.POST.get("snf", request.GET.get("snf", ""))
            clr = request.POST.get("clr", request.GET.get("clr", ""))
            rainfall = request.POST.get("rainfall_mm", request.GET.get("rainfall_mm", ""))
            temperature = request.POST.get("temperature_c", request.GET.get("temperature_c", ""))
            humidity = request.POST.get("humidity_percent", request.GET.get("humidity_percent", ""))

            # Only predict if required features are present
            if fat and snf and rainfall and temperature and humidity:
                fat_val = float(fat)
                snf_val = float(snf)
                clr_val = float(clr or 0)
                rainfall_val = float(rainfall)
                temp_val = float(temperature)
                humidity_val = float(humidity)

                # Create DataFrame with all features
                df = pd.DataFrame([[fat_val, snf_val, clr_val, rainfall_val, temp_val, humidity_val]],
                                  columns=["FAT", "SNF", "CLR", "Rainfall_mm", "Temperature_C", "Humidity_%"])

                # Predict cluster
                cluster = quality_kmeans.predict(df)[0]

                # Map cluster to grade
                grade_map = {0: "C (Low)", 1: "B (Medium)", 2: "A (High)"}
                grade = grade_map.get(cluster, "Unknown")

                result = {"cluster": int(cluster), "grade": grade}

        except Exception as e:
            import traceback
            traceback.print_exc()
            error = f"Error predicting quality: {str(e)}"

    return render(request, "predict_quality.html", {
        "result": result,
        "error": error,
        "fat": fat,
        "snf": snf,
        "clr": clr,
        "rainfall_mm": rainfall,
        "temperature_c": temperature,
        "humidity_percent": humidity
    })


@login_required
def predict_price_page(request):
    """Show price prediction form (with optional prefilled data from quality)"""
    fat = request.GET.get("fat")
    snf = request.GET.get("snf")
    clr = request.GET.get("clr")
    return render(request, "predict_price.html", {"fat": fat, "snf": snf, "clr": clr})

# ============================================================
# 🐄 BREED PREDICTION
# ============================================================

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
import pandas as pd
import joblib
import os

# ✅ Load model safely
try:
    breed_pipe = joblib.load("milkapp/ml_models/breed_pipe.pkl")
    print("✅ Breed model loaded successfully.")
except Exception as e:
    breed_pipe = None
    print(f"❌ Could not load breed model: {e}")

# ✅ Static cost mapping — update as needed
breed_cost_map = {
    "Vechur": 35000,
    "Kasaragod Dwarf": 30000,
    "Jersey Cross": 55000,
    "HF Cross": 70000,
    "Jersey - Red Sindhi": 60000,
    "Sahiwal - HF Cross": 75000,
    "Gir Cross": 65000,
    "Red Sindhi (Pure)": 50000
}

# ✅ Load feed dataset
FEED_DATA_PATH = "milkapp/static/data/feed_data.csv"
FEED_DATA = pd.read_csv(FEED_DATA_PATH) if os.path.exists(FEED_DATA_PATH) else pd.DataFrame()

# ✅ Feed Recommendation Function
def recommend_feed(predicted_breed):
    if FEED_DATA.empty:
        return []

    df = FEED_DATA.copy()

    # Basic rule-based logic
    if predicted_breed in ["HF Cross", "Gir Cross", "Sahiwal - HF Cross"]:
        top_feeds = df[df["Protein_%"] > 25].sort_values(
            ["Milk_Yield_L_per_day", "Protein_%"], ascending=False
        ).head(3)
    elif predicted_breed in ["Jersey Cross", "Jersey - Red Sindhi", "Red Sindhi (Pure)"]:
        top_feeds = df[(df["Protein_%"] >= 15) & (df["Protein_%"] <= 25)].sort_values(
            "Price_Rs_per_quintal"
        ).head(3)
    else:
        top_feeds = df[df["Protein_%"] < 15].sort_values("Price_Rs_per_quintal").head(3)

    # Rename columns for template compatibility
    top_feeds = top_feeds.rename(
        columns={
            "Protein_%": "Protein",
            "Fiber_%": "Fiber",
            "Milk_Yield_L_per_day": "Milk_Yield",
            "Milk_Fat%": "Milk_Fat",
            "Price_Rs_per_quintal": "Price"
        }
    )

    return top_feeds[["Type", "Protein", "Fiber", "Milk_Yield", "Milk_Fat", "Price"]].to_dict("records")

# ✅ Main View: Predict Breed
@login_required
def predict_breed(request):
    result = None
    feeds = []
    error = None

    if breed_pipe is None:
        error = "Breed model not loaded."
        return render(request, "predict_breed.html", {"result": result, "error": error, "feeds": feeds})

    if request.method == "POST":
        try:
            # Helper to safely convert numbers
            def safe_float(value):
                try:
                    return float(value)
                except (TypeError, ValueError):
                    return 0.0

            # ✅ Collect input
            data = {
                "Avg_Milk_Yield_L_per_day": [safe_float(request.POST.get("avg_yield"))],
                "Avg_Fat_%": [safe_float(request.POST.get("avg_fat"))],
                "Avg_SNF_%": [safe_float(request.POST.get("avg_snf"))],
                "Climate_Tolerance": [request.POST.get("climate_tol", "").strip()],
                "Feed_Needs": [request.POST.get("feed_needs", "").strip()],
                "Disease_Resistance_Level": [request.POST.get("disease_res", "").strip()],
                "Use_Type": [request.POST.get("use_type", "").strip()],
            }

            df = pd.DataFrame(data)
            print("\n🧾 Input Data for Prediction:\n", df)

            # ✅ Align with model input
            if hasattr(breed_pipe, "feature_names_in_"):
                expected_cols = breed_pipe.feature_names_in_
                for col in expected_cols:
                    if col not in df.columns:
                        df[col] = 0
                df = df[expected_cols]

            # ✅ Predict
            pred = breed_pipe.predict(df)
            predicted_breed = str(pred[0]).strip().replace("—", "-").replace("  ", " ")
            print("🔹 Predicted Breed:", predicted_breed)

            # ✅ Lookup cost
            breed_cost_map_lower = {k.lower(): v for k, v in breed_cost_map.items()}
            typical_cost = breed_cost_map_lower.get(predicted_breed.lower(), "N/A")

            # ✅ Recommend feeds
            feeds = recommend_feed(predicted_breed)

            # ✅ Final output
            result = {
                "breed": predicted_breed,
                "cost": typical_cost,
            }

            print(f"✅ Result: {result}")
            print(f"🌾 Recommended feeds: {len(feeds)}")

        except Exception as e:
            import traceback
            traceback.print_exc()
            error = f"Error during prediction: {str(e)}"

    return render(request, "predict_breed.html", {"result": result, "feeds": feeds, "error": error})

