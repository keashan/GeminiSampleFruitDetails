import datetime
import os

from flask import Flask, render_template, request
from pathlib import Path
import google.generativeai as genai
from dotenv import load_dotenv


load_dotenv()

app = Flask(__name__)

# Set up the generative model
genai.configure(api_key=os.getenv("API_KEY"))

generation_config = {
    "temperature": 0.4,
    "top_p": 1,
    "top_k": 32,
    "max_output_tokens": 4096,
}

safety_settings = [
    {
        "category": "HARM_CATEGORY_HARASSMENT",
        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
    },
    {
        "category": "HARM_CATEGORY_HATE_SPEECH",
        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
    },
    {
        "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
    },
    {
        "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
    },
]

model = genai.GenerativeModel(
    model_name="gemini-pro-vision",
    generation_config=generation_config,
    safety_settings=safety_settings
)

app.add_url_rule('/temp/<path:filename>', endpoint='temp',
                 view_func=app.send_static_file)

previous_image_path = None  # Define the variable globally


def delete_old_images(path):
    image_folder = path  # Adjust the path to your image folder

    now = datetime.datetime.now()
    one_day_ago = now - datetime.timedelta(days=1)

    for filename in os.listdir(image_folder):
        file_path = os.path.join(image_folder, filename)
        file_stats = os.stat(file_path)
        file_mtime = datetime.datetime.fromtimestamp(file_stats.st_mtime)

        if file_mtime < one_day_ago:
            os.remove(file_path)
            print(f"Deleted old image: {filename}")


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'GET':
        # GET request: Display the index.html form
        return render_template('index.html')


@app.route('/process', methods=['GET', 'POST'])
def process_image():
    global previous_image_path  # Access the global variable

    if request.method == 'POST':
        # data_type = request.args["data_type"]
        image_file = request.files['image']
        if image_file.filename == '':
            return "No image selected"

        # Create the temp/image folder if it doesn't exist
        temp_image_folder = Path('temp/img')
        temp_image_folder.mkdir(parents=True, exist_ok=True)

        delete_old_images(temp_image_folder)

        # Construct the full image path within the temp/image folder
        image_name = image_file.filename
        image_path = temp_image_folder / image_name

        # Delete previous image if it exists
        if previous_image_path and previous_image_path.exists():
            os.remove(previous_image_path)

        # Save the new image and update the previous image path
        image_file.save(image_path)
        previous_image_path = image_path

        image_parts = [
            {
                "mime_type": "image/jpeg",
                "data": image_path.read_bytes()
            },
        ]

        prompt_parts = [
            "look at the following image and give me a small description of it including the name and the origin. If the image is not a fruit, give the error message \"This is not a fruit\". If there is more than one fruit, give the error message \"There are more than one fruit. Please use an image of a single fruit\"\n",
            image_parts[0],
        ]

        response = model.generate_content(prompt_parts)
        return response.text  # render_template('index.html', response=response.text, image_name=image_name)


if __name__ == '__main__':
    app.run(debug=True)
