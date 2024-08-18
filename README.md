# CSVIFY
A Python script to convert a CSV file into a Spotify Playlist


## Getting set up:

### 1. Client ID & Secret (Setting up a Spotify app):
   - Go to https://developer.spotify.com/dashboard
   - Create an app:
       - App Name: [whatever you want, doesn't really matter]
       - App Description: [Also doesn't really matter]
       - Website: [You can just leave this blank]
       - Redirect: If you don't have a website, just use `http://google.com`
   - Click "Save"

### 2. Set environmental variables:
- `CSVIFY_CLIENT_ID`
- `CSVIFY_CLIENT_SECRET`
- `CSVIFY_USER_ID`
- `CSVIFY_USER_TOKEN`
- `CSVIFY_REFRESH_TOKEN`

### 3. Set up your CSV:
- header must contain `track,artist`
- One song per line

### 4. (Optional) download a pic of the cover art:
- Image MUST be in jpg format

## Running the script:
- Prior to running for the first time, make sure you have the required dependencies installed `pip install -r requirements.txt`
- Run the script as such: `python3 ./csvify-playlist.py [path-to-csv] [(optional)-path-to-cover-art]
   - Note: if no cover image is provided, Spotify will roll with the default collage-style cover
