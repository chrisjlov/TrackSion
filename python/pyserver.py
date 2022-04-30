from flask import Flask, request
from flask_cors import CORS, cross_origin
from main import main
import json

app = Flask(__name__)
cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'
JSONdata = ""


@app.route('/getPlaylistJSON', methods = ['POST']) 
@cross_origin()
def postJSON():
    data = json.loads(request.data, strict = False)
    
    recommendedTracks = main(data)
    recommendedTracks = json.dumps(recommendedTracks)

    return recommendedTracks
   
if __name__ == "__main__": 
    app.run(port=5000)
