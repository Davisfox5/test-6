from flask import Flask, jsonify
import random
import string

app = Flask(__name__)

@app.route('/generate', methods=['GET'])
def generate_word():
    letters = string.ascii_lowercase
    word = ''.join(random.choice(letters) for i in range(10))
    return jsonify({'word': word})

if __name__ == "__main__":
    app.run(debug=True)