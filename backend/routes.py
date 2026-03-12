from . import app
import os
import json
import pymongo
from flask import jsonify, request, make_response, abort, url_for  # noqa; F401
from pymongo import MongoClient
from bson import json_util
from pymongo.errors import OperationFailure
from pymongo.results import InsertOneResult
from bson.objectid import ObjectId
import sys

SITE_ROOT = os.path.realpath(os.path.dirname(__file__))
json_url = os.path.join(SITE_ROOT, "data", "songs.json")
songs_list: list = json.load(open(json_url))

# client = MongoClient(
#     f"mongodb://{app.config['MONGO_USERNAME']}:{app.config['MONGO_PASSWORD']}@localhost")
mongodb_service = os.environ.get('MONGODB_SERVICE')
mongodb_username = os.environ.get('MONGODB_USERNAME')
mongodb_password = os.environ.get('MONGODB_PASSWORD')
mongodb_port = os.environ.get('MONGODB_PORT')

print(f'The value of MONGODB_SERVICE is: {mongodb_service}')

if mongodb_service == None:
    app.logger.error('Missing MongoDB server in the MONGODB_SERVICE variable')
    # abort(500, 'Missing MongoDB server in the MONGODB_SERVICE variable')
    sys.exit(1)

if mongodb_username and mongodb_password:
    url = f"mongodb://{mongodb_username}:{mongodb_password}@{mongodb_service}"
else:
    url = f"mongodb://{mongodb_service}"


print(f"connecting to url: {url}")

try:
    client = MongoClient(url)
except OperationFailure as e:
    app.logger.error(f"Authentication error: {str(e)}")

db = client.songs
db.songs.drop()
db.songs.insert_many(songs_list)

def parse_json(data):
    return json.loads(json_util.dumps(data))

######################################################################
# INSERT CODE HERE
######################################################################

# Health endpoint
@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "OK"}), 200

@app.route('/count')
def count():
    """return length of data"""
    count = db.songs.count_documents({})
    return {"count": count}, 200

# GET /song endpoint
@app.route('/song', methods=['GET'])
def songs():
    """return all songs"""
    # Get all songs from the database
    songs = list(db.songs.find({}))
    
    # Parse the songs to handle ObjectId
    parsed_songs = parse_json(songs)
    
    # Return the songs as a list with key "songs"
    return {"songs": parsed_songs}, 200

# GET /song/<id> endpoint
@app.route('/song/<int:id>', methods=['GET'])
def get_song_by_id(id):
    """return song by id"""
    # Find the song by id (not _id)
    song = db.songs.find_one({"id": id})
    
    # If song not found, return 404
    if not song:
        return {"message": "song with id not found"}, 404
    
    # Parse the song to handle ObjectId
    parsed_song = parse_json(song)
    
    # Return the song with 200 OK
    return parsed_song, 200

# POST /song endpoint
@app.route('/song', methods=['POST'])
def create_song():
    """create a new song"""
    
    # Get the song data from the request body
    song = request.get_json()
    
    # Check if a song with the same id already exists
    existing_song = db.songs.find_one({"id": song["id"]})
    
    if existing_song:
        # If song exists, return 302 with message
        return {"Message": f"song with id {song['id']} already present"}, 302
    
    # Insert the new song into the database
    result = db.songs.insert_one(song)
    
    # Return the inserted id with 201 CREATED
    return {"inserted id": parse_json(result.inserted_id)}, 201

# PUT /song/<id> endpoint
@app.route('/song/<int:id>', methods=['PUT'])
def update_song(id):
    """update a song by id"""
    
    # Get the updated song data from the request body
    updated_song = request.get_json()
    
    # Find the existing song
    existing_song = db.songs.find_one({"id": id})
    
    # If song doesn't exist, return 404
    if not existing_song:
        return {"message": "song not found"}, 404
    
    # Check if the update would change anything
    if (existing_song.get('lyrics') == updated_song.get('lyrics') and 
        existing_song.get('title') == updated_song.get('title')):
        return {"message": "song found, but nothing updated"}, 200
    
    # Update the song
    result = db.songs.update_one(
        {"id": id},
        {"$set": {
            "lyrics": updated_song.get('lyrics', existing_song['lyrics']),
            "title": updated_song.get('title', existing_song['title'])
        }}
    )
    
    # Get the updated song
    updated = db.songs.find_one({"id": id})
    
    # Return the updated song with 201 CREATED
    return parse_json(updated), 201


# DELETE /song/<id> endpoint
@app.route('/song/<int:id>', methods=['DELETE'])
def delete_song(id):
    """delete a song by id"""
    
    # Delete the song from the database
    result = db.songs.delete_one({"id": id})
    
    # Check if any document was deleted
    if result.deleted_count == 0:
        # No song found with that id
        return {"message": "song not found"}, 404
    else:
        # Song successfully deleted - return 204 NO CONTENT with empty body
        return "", 204