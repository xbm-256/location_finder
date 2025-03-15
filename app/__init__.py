from flask import Flask
import spacy

app = Flask(__name__)

# Load Spacy model once at startup
nlp = spacy.load('en_core_web_sm')

from app import routes
