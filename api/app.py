from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import re
import time
import concurrent.futures
from pathlib import Path

DATASET = Path(__file__).resolve().parent.parent / 'data' / 'recipes.csv'

app = Flask(__name__)
CORS(app)

# Load your dataset
recipes_data = pd.read_csv(DATASET)

# Clean column names
recipes_data.columns = recipes_data.columns.str.strip()

# Define weights for user preferences
cuisine_weight = 0.2
course_weight = 0.3

# Prepare TF-IDF vectorizer
vectorizer = TfidfVectorizer(binary=True)

# Check if 'ingredients' column exists, if not, use 'ingredients_name'
ingredients_column = 'ingredients' if 'ingredients' in recipes_data.columns else 'ingredients_name'

if ingredients_column not in recipes_data.columns:
    raise ValueError(f"Neither 'ingredients' nor 'ingredients_name' column found in the dataset. Available columns are: {recipes_data.columns.tolist()}")

# Extract and join ingredients into text
recipes_data["ingredients_list"] = recipes_data[ingredients_column].apply(lambda x: str(x).strip().split(","))
recipes_data["ingredients_text"] = recipes_data["ingredients_list"].apply(lambda x: " ".join(x))

# Fit vectorizer and transform recipe ingredients
recipe_vectors = vectorizer.fit_transform(recipes_data["ingredients_text"])

# Update the calculate_weighted_similarity function
def calculate_weighted_similarity(similarity, recipe, user_cuisine, user_course):
    user_pref_similarity = 0
    if user_cuisine and 'cuisine' in recipe:
        # Use the same logic as brute force method
        if any(c.lower() in recipe['cuisine'].lower() for c in user_cuisine):
            user_pref_similarity += cuisine_weight
    if user_course and 'course' in recipe:
        # Use the same logic as brute force method
        if user_course.lower() in recipe['course'].lower():
            user_pref_similarity += course_weight
    weighted_similarity = similarity * (1 - (cuisine_weight + course_weight)) + user_pref_similarity
    return weighted_similarity

def calculate_difficulty(prep_time, cooking_time):
    try:
        total_time = float(prep_time) + float(cooking_time)
        if total_time < 30:
            return 'Easy'
        elif total_time < 60:
            return 'Medium'
        else:
            return 'Hard'
    except ValueError:
        return 'unknown'

def calculate_servings(prep_time, cooking_time):
    try:
        total_time = float(prep_time) + float(cooking_time)
        if total_time < 30:
            return '1 - 2 Servings'
        elif total_time < 60:
            return '4 - 6 Servings'
        else:
            return '6+ Servings'
    except ValueError:
        return 'unknown'

# Update the recommend_recipes function
def recommend_recipes(user_ingredients, user_cuisine, user_course, user_veg):
    # Filter vegetarian recipes if requested
    filtered_recipes = recipes_data[recipes_data['diet'].str.strip().str.lower() == "vegetarian"] if user_veg else recipes_data

    # # Filter by cuisine and course if provided
    # if user_cuisine:
    #     filtered_recipes = filtered_recipes[filtered_recipes['cuisine'].str.lower().apply(lambda x: any(c.lower() in x for c in user_cuisine))]
    # if user_course:
    #     filtered_recipes = filtered_recipes[filtered_recipes['course'].str.lower().str.contains(user_course.lower())]

    # If no recipes match the filters, return an empty list
    if filtered_recipes.empty:
        return []

    # Transform user input
    user_ingredients_text = " ".join(user_ingredients)
    user_vector = vectorizer.transform([user_ingredients_text])

    # Calculate cosine similarity
    similarities = cosine_similarity(user_vector, recipe_vectors[filtered_recipes.index]).flatten()

    # Calculate weighted similarity for each recipe
    weighted_similarities = [
        calculate_weighted_similarity(sim, filtered_recipes.iloc[idx], user_cuisine, user_course)
        for idx, sim in enumerate(similarities)
    ]

    # Get top 24 recommendations
    top_n_indices = np.argsort(weighted_similarities)[-24:][::-1]
    top_recipes = filtered_recipes.iloc[top_n_indices]

    # Use multithreading for preparing recommendations
    with concurrent.futures.ThreadPoolExecutor() as executor:
        recommendations = list(executor.map(
            lambda args: prepare_recommendation(*args),
            [(count, row) for count, (_, row) in enumerate(top_recipes.iterrows(), start=1)]
        ))

    return recommendations

@app.route('/api/recommend-ai', methods=['POST'])
def recommend_recipes_api():
    start_time = time.time()
    data = request.json

    user_ingredients = data.get('ingredients', [])
    user_cuisine = data.get('cuisine', [])
    user_course = data.get('course', '')
    user_veg = data.get('veg', False)

    recommendations = recommend_recipes(user_ingredients, user_cuisine, user_course, user_veg)

    end_time = time.time()
    execution_time = (end_time - start_time) * 1000  # Convert to milliseconds

    return jsonify({
        'recommendations': recommendations,
        'execution_time': round(execution_time, 2),  # Round to 2 decimal places
    })

def prepare_recommendation(count, row):
    return {
        'id': count,
        'title': row['name'].strip(),
        'difficulty': calculate_difficulty(row['prep_time'], row['cook_time']),
        'cooking_time': row['cook_time'].strip(),
        'image': row['image_url'].strip(),
        'veg': row['diet'].strip().lower() == 'vegetarian',
        'cuisine': row['cuisine'].strip(),
        'course': row['course'].strip(),
        'servings': calculate_servings(row['prep_time'], row['cook_time']),
    }

@app.route('/api/recipe', methods=['POST'])
def recipe():
    data = request.json
    name = data.get('name', '').strip().lower()  # Normalize input

    if not name:
        return jsonify({"error": "Recipe name is required"}), 400

    recipes_data = pd.read_csv(DATASET)

    # Strip spaces from column names
    recipes_data.columns = recipes_data.columns.str.strip()

    # Normalize recipe names in the dataset for comparison
    recipes_data['name'] = recipes_data['name'].str.strip().str.lower()

    # Find the recipe
    recipe_list = recipes_data[recipes_data['name'] == name].to_dict('records')

    if not recipe_list:
        return jsonify({"error": "Recipe not found"}), 404

    recipe = recipe_list[0]

    # Calculate difficulty and servings
    difficulty = calculate_difficulty(recipe.get('prep_time'), recipe.get('cook_time'))
    servings = calculate_servings(recipe.get('prep_time'), recipe.get('cook_time'))

    # Prepare the response
    response = {
        'name': recipe.get('name').title(),  # Convert back to title case for response
        'description': recipe.get('description'),
        'veg': recipe.get('diet').strip().lower() == 'vegetarian',  # Handle potential extra spaces
        'image': recipe.get('image_url'),
        'cooking_time': f"{recipe.get('prep_time', 0)} + {recipe.get('cook_time', 0)} mins",
        'serving_size': servings,
        'difficulty': difficulty,
        'course': recipe.get('course'),
        'cooking_ingredients': recipe.get('ingredients_name'),
        'cooking_instruction': recipe.get('instructions')
    }

    return jsonify(response)

def brute_force_recommend(ingredients, cuisine, course, cravings, veg):
    # Preprocess input
    ingredients = [preprocess_text(ing) for ing in ingredients]
    cuisine = [preprocess_text(c) for c in cuisine]
    course = preprocess_text(course)
    cravings = [preprocess_text(crv) for crv in cravings]

    # Create a copy of the dataframe to avoid modifying the original
    df_copy = recipes_data.copy()

    # Preprocess dataframe columns
    df_copy['ingredients_name'] = df_copy['ingredients_name'].apply(preprocess_text)
    df_copy['cuisine'] = df_copy['cuisine'].apply(preprocess_text)
    df_copy['course'] = df_copy['course'].apply(preprocess_text)
    df_copy['description'] = df_copy['description'].apply(preprocess_text)

    # Filter by veg/non-veg
    if veg:
        df_copy = df_copy[df_copy['diet'].str.strip().str.lower() == "vegetarian"]

    # Calculate match scores
    df_copy['ingredient_match'] = df_copy['ingredients_name'].apply(lambda x: sum(ing in x for ing in ingredients))
    df_copy['cuisine_match'] = df_copy['cuisine'].apply(lambda x: any(c in x for c in cuisine))
    df_copy['course_match'] = df_copy['course'].apply(lambda x: course in x)
    df_copy['craving_match'] = df_copy['description'].apply(lambda x: any(crv in x for crv in cravings))

    # Calculate total score
    df_copy['total_score'] = (
        df_copy['ingredient_match'] * 3 +  # Prioritize ingredient matches
        df_copy['cuisine_match'] * 2 +
        df_copy['course_match'] * 2 +
        df_copy['craving_match']
    )

    # Sort by total score and get top 24 results
    results = df_copy.sort_values('total_score', ascending=False).head(24)
    time.sleep(0.08)
    # Prepare results for JSON serialization
    recommendations = []
    for _, row in results.iterrows():
        recommendations.append({
            'id': row.name,  # Use the index as id
            'title': row['name'],
            'difficulty': calculate_difficulty(row['prep_time'], row['cook_time']),
            'cooking_time': row['cook_time'],
            'image': row['image_url'],
            'veg': row['diet'].strip().lower() == 'vegetarian',
            'cuisine': row['cuisine'],
            'course': row['course'],
            'servings': calculate_servings(row['prep_time'], row['cook_time']),
        })

    return recommendations

def preprocess_text(text):
    # Convert to lowercase and remove special characters
    return re.sub(r'[^a-zA-Z0-9\s]', '', str(text).lower())

@app.route('/api/recommend-brute-force', methods=['POST'])
def recommend_brute_force():
    start_time = time.time()
    data = request.json
    ingredients = data.get('ingredients', [])
    cuisine = data.get('cuisine', [])
    course = data.get('course', '')
    cravings = data.get('craving', [])
    veg = data.get('veg', False)

    recommendations = brute_force_recommend(ingredients, cuisine, course, cravings, veg)
    
    
    end_time = time.time()
    execution_time = (end_time - start_time) * 1000  # Convert to milliseconds

    return jsonify({
        'recommendations': recommendations,
        'execution_time': round(execution_time, 2)  # Round to 2 decimal places
    })

if __name__ == '__main__':
    app.run(debug=True)
