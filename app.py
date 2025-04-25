import asyncio
import sys
from flask import Flask, render_template, request, jsonify
import g4f
from g4f.client import Client
import re
import json
import os
 
# Set the event loop policy only on Windows
if sys.platform.startswith('win'):
    from asyncio import WindowsSelectorEventLoopPolicy
    asyncio.set_event_loop_policy(WindowsSelectorEventLoopPolicy())

app = Flask(__name__)
image_client = Client()

# Path to store feedback
FEEDBACK_FILE = 'static/feedback.json'

def generate_recipe_and_image(user_input):
    """
    Generate a recipe and corresponding image using GPT-4o-mini and Flux model.
    """
    try:
        # Check for "restart" command
        if user_input.lower().strip() == "restart":
            return {
                "response": "Chat has been restarted. What recipe would you like me to generate now?",
                "image_url": None
            }

        # System prompt for recipe generation
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a Recipe Generator Chatbot designed to create detailed, personalized recipes based on user input. "
                    "Your purpose is to provide delicious, practical recipes tailored to user preferences (e.g., cuisine type, dietary restrictions, ingredients available). "
                    "Respond to any recipe-related query with a conversational tone and well-structured output. "
                    "Use the following formatting: "
                    "- Start with a friendly greeting or acknowledgment. "
                    "- Use **bold headings** (e.g., **Recipe Name**, **Ingredients**, **Instructions**) for sections. "
                    "- The first heading should always be **Recipe Name** with the name of the dish. "
                    "- Use - or * for bullet points to list ingredients and steps clearly. "
                    "- Include specific ingredients with approximate quantities and calorie counts per serving next to each. "
                    "- Provide step-by-step cooking instructions with practical tips. "
                    "- If the user provides details (e.g., dietary preferences, cuisine, available ingredients), tailor the recipe accordingly. "
                    "- End with a question or prompt to keep the conversation going. "
                    "Keep your tone friendly, encouraging, and informative."
                )
            },
            {"role": "user", "content": user_input}
        ]

        # Generate recipe using GPT-4o-mini
        recipe_response = g4f.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.7,
            top_p=0.9
        )
        recipe_text = recipe_response.strip() if recipe_response else "Sorry, I couldn't process your recipe request."

        # Extract recipe name from the response for image generation
        recipe_name_match = re.search(r"\*\*Recipe Name\*\*\s*\n\s*(.*?)\n", recipe_text)
        recipe_name = recipe_name_match.group(1).strip() if recipe_name_match else user_input

        # Generate image based on the recipe name
        image_prompt = f"A beautifully plated dish of {recipe_name}, vibrant colors, appetizing presentation, high-quality food photography, rustic kitchen setting"
        image_response = image_client.images.generate(
            model="flux",
            prompt=image_prompt,
            response_format="url"
        )
        image_url = image_response.data[0].url if image_response.data else None

        return {
            "response": recipe_text,
            "image_url": image_url
        }

    except Exception as e:
        return {
            "response": f"Error: {e}",
            "image_url": None
        }

@app.route("/")
def landing():
    return render_template("landing.html")

@app.route("/chatbot")
def index():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    user_input = data.get("message", "")
    result = generate_recipe_and_image(user_input)
    return jsonify(result)

@app.route("/feedback", methods=["POST"])
def submit_feedback():
    try:
        data = request.get_json()
        feedback = data.get("feedback", "")
        rating = data.get("rating", 5)  # Default to 5 if not provided
        if not feedback:
            return jsonify({"error": "Feedback cannot be empty"}), 400

        # Load existing feedback
        feedback_list = []
        if os.path.exists(FEEDBACK_FILE):
            with open(FEEDBACK_FILE, 'r') as f:
                feedback_list = json.load(f)

        # Append new feedback
        feedback_list.append({
            "feedback": feedback,
            "rating": rating,
            "timestamp": request.json.get("timestamp", "")
        })

        # Save updated feedback
        with open(FEEDBACK_FILE, 'w') as f:
            json.dump(feedback_list, f, indent=2)

        return jsonify({"message": "Feedback submitted successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/feedback", methods=["GET"])
def get_feedback():
    try:
        if os.path.exists(FEEDBACK_FILE):
            with open(FEEDBACK_FILE, 'r') as f:
                feedback_list = json.load(f)
            return jsonify(feedback_list)
        return jsonify([])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/feedback_page")
def feedback_page():
    return render_template("feedback.html")

if __name__ == "__main__":
    app.run(debug=True)
