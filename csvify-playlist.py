import json
import pandas as pd
import requests
import os
import sys
import base64
import requests.utils
from urllib.parse import quote  # Used for encoding special characters in URLs
from dotenv import load_dotenv

class CreatePlaylist:
    
    def __init__(self, csv_path):
        load_dotenv()
        # Assign environment variables to class attributes
        self.user_id = os.getenv('CSVIFY_USER_ID')
        self.token = os.getenv('CSVIFY_TOKEN')
        self.client_id = os.getenv('CSVIFY_CLIENT_ID')
        self.client_secret = os.getenv('CSVIFY_CLIENT_SECRET')
        self.refresh_token = os.getenv('CSVIFY_REFRESH_TOKEN')
        self.csv = csv_path
        self.tuples = self.get_song_names()  # Grab song names and artists from CSV

    # Refresh Spotify token when it expires
    def refresh_access_token(self):
        url = "https://accounts.spotify.com/api/token"
        headers = {
            # Authorization header for Spotify API
            "Authorization": f"Basic {base64.b64encode(f'{self.client_id}:{self.client_secret}'.encode()).decode()}"
        }
        data = {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token
        }
        # Make a POST request to the Spotify API to refresh the token
        response = requests.post(url, headers=headers, data=data)
        response_data = response.json()

        if response.status_code == 200:  # If the request is successful
            self.token = response_data.get("access_token")  # Update the access token
            print("Access token refreshed successfully.")
        else:
            print(f"Error refreshing token: {response_data.get('error_description')}")
            self.token = None  # Set token to None if refresh failed

    # Make request to the Spotify API with proper auth handling
    def make_request(self, url, method='GET', data=None, headers=None):
        headers = headers or {}
        headers["Authorization"] = f"Bearer {self.token}"
        
		# Send the request
        response = requests.request(method, url, headers=headers, data=data)  
        
        if response.status_code == 401:  # Token expired, need to refresh it
            self.refresh_access_token()
            if not self.token:  # Fail if failed to refresh
                print("Failed to refresh access token.")
                return None
            
            headers["Authorization"] = f"Bearer {self.token}"  # Update headers with new token
            response = requests.request(method, url, headers=headers, data=data)  # Retry request
        
        return response

    # Retrieve song names and artists from CSV 
    def get_song_names(self):
        df = pd.read_csv(self.csv)  # Read the CSV into dataframe
        return list(zip(df.track, df.artist))  # Return a list of tuples (song, artist)

    # Create new playlist
    def create_playlist(self):
        playlist_name = os.path.splitext(os.path.basename(self.csv))[0]  # Use the CSV filename as the playlist name
        request_body = json.dumps({
            "name": playlist_name,
            "description": "Playlist generated via CSV with: https://github.com/abraxas86/csv-to-playlist/",
            "public": True  # Make the playlist public
        })
        url = f"https://api.spotify.com/v1/users/{self.user_id}/playlists"
        response = self.make_request(url, method='POST', data=request_body)  # Send a POST request to create the playlist
        
        if response and response.status_code == 201:  # 201 = success
            response_json = response.json()
            print(f"Playlist created successfully: {response_json['id']}")
            return response_json["id"]  # Return the new playlist's ID
        else:
            print(f"Error creating playlist: {response.text}")
        
        return None

    # Get the Spotify URI for a song based on title and artist
    def get_spotify_uri(self, song, artist):
        # Encode song/artist to handle special characters
        song_encoded = quote(song)
        artist_encoded = quote(artist)

        query = f"track:{song_encoded} artist:{artist_encoded}"  # Create search query string
        print(f"Searching for: {query}")
        url = f"https://api.spotify.com/v1/search?query={query}&type=track&offset=0&limit=1"
        response = self.make_request(url)  # Send GET request to search for the song
        
        if response:
            response_json = response.json()
            songs = response_json.get("tracks", {}).get("items", [])  # Get list of tracks from the response
            if not songs:
                print(f"No tracks found for {song} by {artist}")
            return songs[0]["uri"] if songs else None  # Return the URI of the first matching song/Return None if no match

    # Upload cover image to playlist
    def upload_playlist_cover(self, playlist_id, image_path):
        # Convert image to Base64
        with open(image_path, 'rb') as image_file:
            image_data = image_file.read()
        
        base64_image = base64.b64encode(image_data).decode('utf-8')
        
        # Set content type for Base64 image upload
        url = f"https://api.spotify.com/v1/playlists/{playlist_id}/images"
        response = self.make_request(url, method='PUT', data=base64_image, headers={"Content-Type": "image/jpeg"})
        
        if response:
            print(f"Cover image upload response status code: {response.status_code}")
            if response.status_code == 202:  # Status 202 = success
                print("Cover image uploaded successfully.")
            else:
                print(f"Error uploading cover image: {response.text}")
        else:
            print("Failed to upload cover image, no response received.")

    # Add songs to the created playlist
    def add_to_playlist(self, image_path=None):
        uris = []
        for song, artist in self.tuples:
            uri = self.get_spotify_uri(song, artist)  # Get Spotify URI for each song
            if uri:
                uris.append(uri)  # Add URI to the list if found

        if not self.token:  # Confirm valid token
            self.refresh_access_token()

        if not self.token:
            print("Unable to refresh access token.")
            return

        playlist_id = self.create_playlist()  # Create playlist
        if not playlist_id:
            return

        print(f"Collected URIs: {uris}")

        # Add songs to the playlist in batches of 100 (Spotify's limit for batch adding tracks)
        batch_size = 100
        for i in range(0, len(uris), batch_size):
            batch_uris = uris[i:i + batch_size]
            request_data = json.dumps({"uris": batch_uris})
            url = f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks"

            response = self.make_request(url, method='POST', data=request_data)  # Add tracks to the playlist
            
            if response and response.status_code == 201:
                print(f"Successfully added tracks to playlist.")
            else:
                print(f"Error adding tracks: {response.text}")

        if image_path:  # If an image path is provided, upload the cover image
            print(f"Attempting to upload cover image from: {image_path}")
            self.upload_playlist_cover(playlist_id, image_path)

if __name__ == '__main__':
    if len(sys.argv) < 2:  # Ensure that a CSV path is provided as an argument
        print("Usage: python3 playlistGenerator.py <path_to_csv> [<path_to_image>]")
        sys.exit(1)
    
    csv_path = sys.argv[1]
    image_path = sys.argv[2] if len(sys.argv) == 3 else None  # Optional image path for the playlist cover
    cp = CreatePlaylist(csv_path)
    cp.add_to_playlist(image_path)

