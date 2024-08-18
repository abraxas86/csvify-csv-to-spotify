import json
import pandas as pd
import requests
import os
import sys
import base64
import requests.utils
from my_secrets import token, user_id, client_id, client_secret, refresh_token

class CreatePlaylist:
    
    def __init__(self, csv_path):
        self.user_id = user_id
        self.token = token
        self.refresh_token = refresh_token
        self.client_id = client_id
        self.client_secret = client_secret
        self.csv = csv_path
        self.tuples = self.get_song_names()

    def refresh_access_token(self):
        url = "https://accounts.spotify.com/api/token"
        headers = {
            "Authorization": f"Basic {base64.b64encode(f'{self.client_id}:{self.client_secret}'.encode()).decode()}"
        }
        data = {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token
        }
        response = requests.post(url, headers=headers, data=data)
        response_data = response.json()

        if response.status_code == 200:
            self.token = response_data["access_token"]
            print("Access token refreshed successfully.")
        else:
            print(f"Error refreshing token: {response_data}")
            self.token = None

    def make_request(self, url, method='GET', data=None, headers=None):
        if headers is None:
            headers = {}
        
        headers["Authorization"] = f"Bearer {self.token}"
        
        response = requests.request(method, url, headers=headers, data=data)
        
        if response.status_code == 401:  # Token expired
            self.refresh_access_token()
            if not self.token:
                print("Failed to refresh access token.")
                return None
            
            headers["Authorization"] = f"Bearer {self.token}"
            response = requests.request(method, url, headers=headers, data=data)
        
        return response

    def get_song_names(self):
        df = pd.read_csv(self.csv)
        tuple_list = list(zip(df.track, df.artist))
        return tuple_list

    def create_playlist(self):
        playlist_name = os.path.splitext(os.path.basename(self.csv))[0]
        request_body = json.dumps({
            "name": playlist_name,
            "description": "Playlist generated via CSV with: https://github.com/abraxas86/csv-to-playlist/",
            "public": True
        })
        query = f"https://api.spotify.com/v1/users/{self.user_id}/playlists"
        response = self.make_request(query, method='POST', data=request_body)
        
        if response:
            response_json = response.json()
            if response.status_code == 201:
                print(f"Playlist created successfully: {response_json['id']}")
                return response_json["id"]
            else:
                print(f"Error creating playlist: {response_json}")
        
        return None

    def get_spotify_uri(self, song, artist):
        song = song.replace("'", "")
        artist = artist.replace("'", "")

        query = f"track:{requests.utils.quote(song)} artist:{requests.utils.quote(artist)}"
        print(f"Searching for: {query}")
        url = f"https://api.spotify.com/v1/search?query={query}&type=track&offset=0&limit=1"
        response = self.make_request(url)
        
        if response:
            response_json = response.json()
            songs = response_json.get("tracks", {}).get("items", [])
            if not songs:
                print(f"No tracks found for {song} by {artist}")

            return songs[0]["uri"] if songs else None

    def upload_playlist_cover(self, playlist_id, image_path):
        # Convert image to Base64
        with open(image_path, 'rb') as image_file:
            image_data = image_file.read()
        
        base64_image = base64.b64encode(image_data).decode('utf-8')
        image_data = base64_image
        
        # Set Content-Type for Base64
        url = f"https://api.spotify.com/v1/playlists/{playlist_id}/images"
        response = self.make_request(url, method='PUT', data=image_data, headers={"Content-Type": "image/jpeg"})
        
        print(f"Cover image upload response status code: {response.status_code}")
        if response.status_code == 200:
            print("Cover image uploaded successfully.")
        else:
            print(f"Error uploading cover image: {response.text}")

    def add_to_playlist(self, image_path=None):
        uris = []

        for song, artist in self.tuples:
            uri = self.get_spotify_uri(song, artist)
            if uri:
                uris.append(uri)
            else:
                print(f"Could not find URI for {song} by {artist}")

        if not self.token:
            self.refresh_access_token()

        if not self.token:
            print("Unable to refresh access token.")
            return

        playlist_id = self.create_playlist()
        if not playlist_id:
            return

        print(f"Collected URIs: {uris}")

        batch_size = 100
        for i in range(0, len(uris), batch_size):
            batch_uris = uris[i:i + batch_size]
            request_data = json.dumps({"uris": batch_uris})
            query = f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks"

            response = self.make_request(query, method='POST', data=request_data)
            
            if response:
                response_json = response.json()
                print(f"Response adding tracks: {response_json}")

                if response.status_code != 201:
                    print(f"Error adding tracks: {response_json}")
                else:
                    print(f"Successfully added tracks to playlist: {response_json}")

        if image_path:
            print(f"Attempting to upload cover image from: {image_path}")
            self.upload_playlist_cover(playlist_id, image_path)

        return response_json

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 playlistGenerator.py <path_to_csv> [<path_to_image>]")
        sys.exit(1)
    
    csv_path = sys.argv[1]
    image_path = sys.argv[2] if len(sys.argv) == 3 else None
    cp = CreatePlaylist(csv_path)
    cp.add_to_playlist(image_path)

