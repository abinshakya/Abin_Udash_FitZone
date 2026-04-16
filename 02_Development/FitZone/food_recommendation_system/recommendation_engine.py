import os
import pickle
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from django.conf import settings

# Load pre-trained models and data
MODEL_PATH = os.path.join(settings.BASE_DIR, 'food_recommendation_system', 'food_models.pkl')

try:
    with open(MODEL_PATH, 'rb') as f:
        models_data = pickle.load(f)
        dt_model = models_data['dt_model']
        scaler_original = models_data['scaler']
        cosine_sim = models_data['cosine_sim']
        df_clean = models_data['df_clean']
except Exception:
    dt_model = None
    scaler_original = None
    cosine_sim = None
    df_clean = None

def get_recommendations(
    age, height, current_weight, target_weight, gender="M", 
    activity_level="moderate", food_pref="both", cuisine="all",
    kcal_per_kg=110.0, min_daily_cal=1200.0, 
    max_delta_kcal=900.0, cap_factor=1.5, w_health=0.45, w_macro=0.35, w_ingred=0.20
):
    if df_clean is None:
        return {"error": "Models not loaded. Please ensure food_models.pkl exists."}

    def bmi_info(w_kg, h_cm):
        bmi_val = w_kg / ((h_cm / 100) ** 2)
        if bmi_val < 18.5:
            cat = "underweight"
        elif bmi_val < 25:
            cat = "normal"
        elif bmi_val < 30:
            cat = "overweight"
        else:
            cat = "obese"
        return bmi_val, cat
    
    bmi_val, bmi_cat = bmi_info(current_weight, height)
    
    if gender.upper() == "M":
        bmr = 10 * current_weight + 6.25 * height - 5 * age + 5
    else:
        bmr = 10 * current_weight + 6.25 * height - 5 * age - 161
    
    activity_map = {
        "sedentary": 1.2,
        "light": 1.375,
        "moderate": 1.55,
        "active": 1.725,
        "very_active": 1.9
    }
    activity_mult = activity_map.get(activity_level.lower(), 1.55)
    tdee = bmr * activity_mult
    
    diff = target_weight - current_weight
    direction = "loss" if diff < 0 else "gain"
    
    delta_kcal = np.clip(abs(diff) * kcal_per_kg, 250.0, max_delta_kcal)
    
    if direction == "loss":
        target_cal = max(min_daily_cal, tdee - delta_kcal)
    else:
        target_cal = tdee + delta_kcal
    
    per_meal_target = target_cal / 3.0
    calorie_cap = per_meal_target * cap_factor
    calorie_range = (max(180.0, per_meal_target * 0.65), min(calorie_cap, per_meal_target + 350.0))
    
    if direction == "loss":
        macro_split = {"protein": 0.37, "fat": 0.25, "carbs": 0.38}
    elif direction == "gain":
        macro_split = {"protein": 0.28, "fat": 0.30, "carbs": 0.42}
    else:
        macro_split = {"protein": 0.30, "fat": 0.30, "carbs": 0.40}
    
    filtered_df = df_clean.copy()
    
    if food_pref.lower() in ["veg", "non-veg"]:
        filtered_df = filtered_df[filtered_df["food_type"] == food_pref.lower()]
    
    filtered_df = filtered_df[
        (filtered_df["calories"] >= calorie_range[0]) &
        (filtered_df["calories"] <= calorie_range[1])
    ]
    
    if cuisine.lower() != "all":
        filtered_df = filtered_df[filtered_df["cuisine_type"].apply(lambda x: cuisine.lower() in [c.lower() for c in x])]
    
    if len(filtered_df) == 0:
        return {
            "meta": {
                "bmi": round(bmi_val, 2),
                "bmi_category": bmi_cat,
                "target_calories": round(target_cal, 0),
                "calorie_range": (round(calorie_range[0], 0), round(calorie_range[1], 0))
            },
            "error": "No recipes match your criteria. Try adjusting preferences."
        }
    
    features = ["calories", "protein", "fat", "carbs"]
    X_df = filtered_df[features]
    try:
        if hasattr(dt_model, "predict_proba"):
            dt_proba = dt_model.predict_proba(X_df)[:, 1]
        else:
            dt_proba = dt_model.predict(X_df).astype(float)
    except:
        dt_proba = np.ones(len(filtered_df))
    
    filtered_df["health_score"] = dt_proba
    
    # We use a fresh scaler to normalize the distances for this subset
    scaler = StandardScaler()
    X_scaled_array = scaler.fit_transform(X_df)
    
    target_macros = pd.DataFrame([[
        filtered_df["calories"].mean(),
        filtered_df["calories"].mean() * macro_split["protein"],
        filtered_df["calories"].mean() * macro_split["fat"],
        filtered_df["calories"].mean() * macro_split["carbs"]
    ]], columns=features)
    target_macros_scaled = scaler.transform(target_macros)
    
    distances = np.linalg.norm(X_scaled_array - target_macros_scaled, axis=1)
    knn_scores = 1.0 / (1.0 + distances)
    
    filtered_df["knn_score"] = knn_scores
    
    filtered_indices = filtered_df.index.tolist()
    
    # Compute ingredient similarity based on global cosine_sim
    ingred_similarity = cosine_sim[filtered_indices][:, filtered_indices].mean(axis=1)
    
    filtered_df["ingred_score"] = ingred_similarity
    
    def normalize_signal(signal):
        min_val, max_val = signal.min(), signal.max()
        if max_val == min_val:
            return np.ones(len(signal))
        return (signal - min_val) / (max_val - min_val)
    
    health_norm = normalize_signal(filtered_df["health_score"].values)
    knn_norm = normalize_signal(filtered_df["knn_score"].values)
    ingred_norm = normalize_signal(filtered_df["ingred_score"].values)
    
    filtered_df["final_score"] = (
        w_health * health_norm + 
        w_macro * knn_norm + 
        w_ingred * ingred_norm
    )
    
    def get_meals(meal_type_filter, n_meals=3, excluded_indices=None):
        if excluded_indices is None:
            excluded_indices = set()
        
        meals_data = filtered_df[
            filtered_df["meal_type"].apply(lambda x: meal_type_filter.lower() in [m.lower() for m in x])
        ]
        
        meals_data = meals_data[~meals_data.index.isin(excluded_indices)]
        
        # Sort by final score and get slightly more to allow for daily variation
        # We'll take top 21 (3 meals * 7 days) if available to pick different ones each day
        meals_data = meals_data.sort_values("final_score", ascending=False).head(21)
        
        if len(meals_data) < n_meals:
            remaining = filtered_df[~filtered_df.index.isin(excluded_indices | set(meals_data.index))]
            remaining = remaining.sort_values("final_score", ascending=False).head(21 - len(meals_data))
            meals_data = pd.concat([meals_data, remaining])
        
        return [
            {
                "name": row["recipe_name"],
                "image": row["image_url"], # Changed from image_url to image
                "calories": round(row["calories"], 1),
                "protein": round(row["protein"], 1), # Changed from protein_g to protein
                "fat": round(row["fat"], 1), # Changed from fat_g to fat
                "carbs": round(row["carbs"], 1), # Changed from carbs_g to carbs
                "cuisine": ", ".join(row["cuisine_type"]) if row["cuisine_type"] else "Unknown",
                "ingredients": "\n".join(row["ingredient_lines"]) if row["ingredient_lines"] else "Check recipe details for full ingredient list.",
                "instructions": f"To view full preparation steps, please visit: {row['url']}" if 'url' in row and row['url'] else "Follow standard preparation steps for this meal type.",
                "health_score": round(row["health_score"], 3),
                "macro_score": round(row["knn_score"], 3),
                "ingredient_score": round(row["ingred_score"], 3),
                "final_score": round(row["final_score"], 3)
            }
            for _, row in meals_data.iterrows()
        ], set(meals_data.index)
    
    # Get pools of meals
    breakfast_pool, breakfast_indices = get_meals("breakfast", 21, set())
    lunch_pool, lunch_indices = get_meals("lunch", 21, breakfast_indices)
    dinner_pool, dinner_indices = get_meals("dinner", 21, breakfast_indices | lunch_indices)
    
    # Generate a full weekly plan (7 days) with different food each day
    days = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    weekly_plan = {}
    
    for i, day in enumerate(days):
        # Slice the pools to get different meals for different days
        # Each day gets 3 unique options from the pool (3 * 7 = 21)
        start = i * 3
        end = start + 3
        
        weekly_plan[day] = {
            "breakfast": breakfast_pool[start:end] if i*3 < len(breakfast_pool) else breakfast_pool[:3],
            "lunch": lunch_pool[start:end] if i*3 < len(lunch_pool) else lunch_pool[:3],
            "dinner": dinner_pool[start:end] if i*3 < len(dinner_pool) else dinner_pool[:3]
        }

    return {
        "meta": {
            "bmi": round(bmi_val, 2),
            "bmi_category": bmi_cat,
            "current_weight": current_weight,
            "target_weight": target_weight,
            "weight_goal": direction.upper(),
            "target_calories": round(target_cal, 0),
            "calorie_range": (round(calorie_range[0], 0), round(calorie_range[1], 0)),
            "tdee": round(tdee, 0),
            "macro_split": macro_split
        },
        "breakfast": breakfast_pool[:3], # Fallback for old code
        "lunch": lunch_pool[:3],
        "dinner": dinner_pool[:3],
        "weekly_plan": weekly_plan
    }


