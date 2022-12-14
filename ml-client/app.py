from flask import Flask, render_template, request, redirect, url_for, make_response
from dotenv import load_dotenv
from styleTransfer import *
import filetype
import requests
import pymongo
import base64
import os

app = Flask(__name__)

model = initialize()

def is_docker():
    path = '/proc/self/cgroup'
    return (
        os.path.exists('/.dockerenv') or
        os.path.isfile(path) and any('docker' in line for line in open(path))
    )

if(is_docker()):
    client = pymongo.MongoClient("db", 27017)
else:
    client = pymongo.MongoClient("127.0.0.1", 27017)

db=client["Team5"]

# route for the home page
@app.route('/')
def home():
    """
    Route for the home page
    """
    return render_template('home.html') # render the home template

@app.route('/url', methods=["GET", "POST"])
def url():
    if(request.method == "GET"):
        return render_template("url.html")
    acceptedFormats = ["jpg", "jpeg", "png", "bmp"]
    try:
        contentImageContent = requests.get(request.form["contentImageURL"]).content
    except:
        return render_template("url.html", error="Content image url is invalid. Either save and upload the image using the upload option, or pick a different content image with a valid extension in the url.")
    try:
        styleImageContent = requests.get(request.form["styleImageURL"]).content
    except:
        return render_template("url.html", error="Style image url is invalid. Either save and upload the image using the upload option, or pick a different style image with a valid extension in the url.")
    try:
        contentExt = filetype.guess(contentImageContent).extension
    except:
        return render_template("url.html", error="Problem deciphering the filetype of content image, image may be temporarily down or has an invalid extension, use another content image.")
    try:
        styleExt = filetype.guess(styleImageContent).extension
    except:
        return render_template("url.html", error="Problem deciphering the filetype of style image, image may be temporarily down or has an invalid extension, use another style image.")
    if(contentExt not in acceptedFormats or styleExt not in acceptedFormats):
        return render_template("url.html", error="Please enter images in valid formats (.jpg, .jpeg, .png, .bmp)")
    contentImageURI = "data:image/" + contentExt + ";base64," + base64.b64encode(contentImageContent).decode()
    styleImageURI = "data:image/" + styleExt + ";base64," + base64.b64encode(styleImageContent).decode()
    stylizedImageURI = url_perform_style_transfer(model, request.form["contentImageURL"], request.form["styleImageURL"])
    if(type(stylizedImageURI) == list):
        if(len(stylizedImageURI) == 2):
            return render_template("url.html", error="Was not able to retrieve content and style images due to a retrieval error. Please use other images.")
        if(len(stylizedImageURI) == 1):
            return render_template("url.html", error="Was not able to retrieve " + stylizedImageURI[0] + " image due to a retrieval error. Please use another image.")
    try:
        db.images.insert_one({
            'contentImageURI': contentImageURI,
            'styleImageURI': styleImageURI,
            'stylizedImageURI': stylizedImageURI
        })
    except:
        pass
    return render_template('url.html', contentImageURI=contentImageURI, styleImageURI=styleImageURI, stylizedImageURI=stylizedImageURI)

@app.route('/upload', methods=["GET", "POST"])
def upload():
    if(request.method == "GET"):
        return render_template("upload.html")
    basepath = "./static/images/"
    contentImage = basepath + request.form["contentImage"]
    styleImage = basepath + request.form["styleImage"]
    acceptedFormats = ["jpg", "jpeg", "png", "bmp"]
    try:
        contentExt = filetype.guess(contentImage).extension
    except:
        return render_template("upload.html", error="Content image cannot be found in static/images directory")
    try:
        styleExt = filetype.guess(styleImage).extension
    except:
        return render_template("upload.html", error="Style image cannot be found in static/images directory")
    if(contentExt not in acceptedFormats and styleExt not in acceptedFormats):
        return render_template("upload.html", error="Invalid content and style images format. Upload content and style images in one of these formats (.jpg, .jpeg, .png, .bmp)")
    if(contentExt not in acceptedFormats):
        return render_template("upload.html", error="Invalid content image format. Upload content image in one of these formats (.jpg, .jpeg, .png, .bmp)")
    if(styleExt not in acceptedFormats):
        return render_template("upload.html", error="Invalid style image format. Upload style image in one of these formats (.jpg, .jpeg, .png, .bmp)")
    images = uploaded_perform_style_transfer(model, contentImage, styleImage)
    try:
        db.images.insert_one({
            'contentImageURI': images[0],
            'styleImageURI': images[1],
            'stylizedImageURI': images[2]
        })
    except:
        pass
    return render_template("upload.html", contentImageURI=images[0], styleImageURI=images[1], stylizedImageURI=images[2])