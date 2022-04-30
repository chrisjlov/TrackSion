import spotipy
import pandas as pd
import time
import requests
import base64
import urllib.parse
import dateutil.parser as parser
from spotipy.oauth2 import SpotifyClientCredentials
from sklearn.neighbors import NearestNeighbors
from sklearn.naive_bayes import GaussianNB


clientId = '259fc2a05c5645a5bf0fa70b0910d057'
clientSecret = 'f5383ba38661492bb5b4762dc500b2c6'

client_credentials_manager = SpotifyClientCredentials(client_id=clientId, client_secret=clientSecret)
sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)


authURL = "https://accounts.spotify.com/api/token"
authHeader = {}
authData = {}

playlistLength = 0
JSONdata = ""


def main(data):
    # Set Access Token to global variable
    global token
    token = getAccessToken(clientId, clientSecret)
    playlistInfo = getPlaylistInfo(data)
    playlistLength = len(playlistInfo)
    playlistTrackIds = getSongList(playlistInfo)
    playlistFeatures = getFeatures(playlistInfo, playlistTrackIds, 0)
    
    # print(playlistInfo)
    # print(playlistLength)
    # print(playlistTrackIds)
    # print(playlistFeatures)

    recommendedPlaylist = getTrackRecommendations(playlistTrackIds, 5)
    recommendedTrackIds = getSongList(recommendedPlaylist)
    recommendedFeatures = getFeatures(recommendedPlaylist, recommendedTrackIds, 1)
    # print(recommendedPlaylist)
    # print(recommendedTrackIds)
    # print(recommendedFeatures)

    listOfOrginalFeatures = getOrignalFeaturesIntoList(
        playlistFeatures, playlistLength)
    listOfRecommendedFeatures = getRecommendedFeaturesIntoList(
        recommendedFeatures, playlistLength)


    # print(listOfOrgianalFeatures)
    
    # print(listOfRecommendedFeatures)

    knnList = knn(listOfOrginalFeatures,
                  listOfRecommendedFeatures, playlistLength)
    # print(knnList)
    finalKNN = getFinalRecommendations(
        knnList, playlistTrackIds, playlistFeatures, 1)
    # print(finalKNN)
    # List of KNN recommendations track ids are set to a global variable
    knnTrackIds = getSongList(finalKNN)
    # Dataframe of KNN recommendations track features are set to a global variable
    #knnFeaturesSet = getFeatures(finalKNN, knnTrackIds)
    knnFeaturesSet = getFeatures(finalKNN, knnTrackIds,1)
    # print(knnFeaturesSet)
    naiveBayes(knnFeaturesSet, playlistLength)

    return knnTrackIds


def getAccessToken(clientId, clientSecret):

    # Creates Access Token.
    # Parameters: (clientId, clientSecret) Spotify API client Id and client secret.
    # Returns: Access Token. Example (BQB5uYjC0tcVsvs41Bk3j8CT_DEzAwwuiDHKPfmEEp_Pc22r1cDMmc8aB3Xbgsp3RJPqm5M7oSILKKmF6Ug)

    # Base64 Encode Client ID and Secret
    message = f"{clientId}:{clientSecret}"
    message_bytes = message.encode('ascii')
    base64_bytes = base64.b64encode(message_bytes)
    based64_message = base64_bytes.decode('ascii')

    authHeader['Authorization'] = "Basic " + based64_message
    authData['grant_type'] = "client_credentials"
    res = requests.post(authURL, headers=authHeader, data=authData)

    responseObject = res.json()
    accessToken = responseObject['access_token']
    return accessToken


def getPlaylistInfo(playlist):
    # Takes track data in JSON format and puts the track details and puts them into a dataframe and returns the dataframe
    # Parameters: (playlist) JSON formatted Data.
    # Returns: Data Frame of orginal playlist

    index = 0

    # Attributes that are taken from the playlist JSON data to be put in dataframe
    trackInfo = pd.DataFrame(
        columns=('TrackName', 'TrackId', 'ArtistName', "ArtistId", "Date", "Popularity", "Duration"))

    for item in playlist['newTracks']:
        albumDate = parser.parse(item['date']).year
        duration = int((item['duration']/(1000*60)) % 60)
        trackInfo.loc[index] = item['trackName'], item['trackId'], item['artistId'], item['artistId'], albumDate, item['popularity'], duration
        index += 1

    return trackInfo

# Data frame of original playlist
# playlistInfo = getPlaylistInfo(playlistData)
# #Length of original playlist
# playlistLength = len(playlistInfo)


def getSongList(playlist):
    # Creates a list of the given playlist dataframe of the track ids
    # Parameters: (playlist) Data frame of playlist.
    # Returns: list of Track Ids
    tracksIds = ""
    indivdualTracksId = list(playlist['TrackId'])
    tracksIds = (indivdualTracksId)
    return tracksIds

# Sets list of Track Ids to global variable
# playlistTrackIds = getSongList(playlistInfo)


def getFeatures(playlist, playlistTrackIds, getGenre):
    # Takes in playlist data frame and track ids list and returns a data frame with the tracks features(Danceability, energy, loudness, speechiness, acousticness, valence, instrumentalness, tempo, genre)
    # Parameters: (playlist, playlistTrackIds, getGenre) Playlist data frame, track ids list, an int to decide whether or not to include the tracks genre.
    # Returns: Data frame with the track details and features

    #if getGenre == 0, include the genre, else don't
    if(getGenre == 0):
        index = 0
        # Dataframe with the track details and features
        featureInfo = pd.DataFrame(columns=('TrackId', 'TrackName', 'ArtistId', 'ArtistName', 'Date', 'Danceability', 'Energy', 'Loudness',
                                            'Speechiness', 'Acousticness', 'Valence', 'Instrumentalness', 'Tempo', 'Key', 'Liveness', 'TimeSignature', 'Genres', 'Popularity', 'Duration'))

        for track in playlistTrackIds:
            audioFeatures = sp.audio_features(track)
            # Web limitation, try and except allows breathing room for the API calls to refresh
            try:
                # Grabs artist details and sets the artist's genre for the track
                artist_info = sp.artist(playlist.loc[index, 'ArtistId'])
                artist_genres = artist_info["genres"]
            except:
                print(
                    'ERROR Caught while trying to get Artist Genre: trying again. Index =', index)
                try:
                    time.sleep(1)
                    artist_info = sp.artist(playlist.loc[index, 'ArtistId'])
                    artist_genres = artist_info["genres"]
                except:
                    # Unable to get artist's genre, either means API call limit reached, or track has no genre which 
                    # could be the case as not all tracks have a given genre
                    print(
                        'ERROR Caught Again while trying to get Artist Genre: Setting Genre to N/A. Index =', index)
                    artist_genres = "N/A"

            # Set each tracks details and features into dataframe
            featureInfo.loc[index] = [track, playlist.loc[index, 'TrackName'], playlist.loc[index, 'ArtistId'], playlist.loc[index, 'ArtistName'], playlist.loc[index, 'Date'], audioFeatures[0]['danceability'], audioFeatures[0]['energy'], audioFeatures[0]['loudness'], audioFeatures[0]
                                      ['speechiness'], audioFeatures[0]['acousticness'], audioFeatures[0]['valence'], audioFeatures[0]['instrumentalness'], audioFeatures[0]['tempo'], audioFeatures[0]['liveness'], audioFeatures[0]['key'], audioFeatures[0]['time_signature'], artist_genres, playlist.loc[index, 'Popularity'], playlist.loc[index, 'Duration']]
            index += 1

    else:
        index = 0
        # Dataframe with the track details and features
        featureInfo = pd.DataFrame(columns=('TrackId', 'TrackName', 'ArtistId', 'ArtistName', 'Date', 'Danceability', 'Energy', 'Loudness',
                                            'Speechiness', 'Acousticness', 'Valence', 'Instrumentalness', 'Tempo', 'Key', 'Liveness', 'TimeSignature', 'Popularity', 'Duration'))

        for track in playlistTrackIds:
            audioFeatures = sp.audio_features(track)

            # Set each tracks details and features into dataframe
            featureInfo.loc[index] = [track, playlist.loc[index, 'TrackName'], playlist.loc[index, 'ArtistId'], playlist.loc[index, 'ArtistName'], playlist.loc[index, 'Date'], audioFeatures[0]['danceability'], audioFeatures[0]['energy'], audioFeatures[0]['loudness'], audioFeatures[0]
                                      ['speechiness'], audioFeatures[0]['acousticness'], audioFeatures[0]['valence'], audioFeatures[0]['instrumentalness'], audioFeatures[0]['tempo'], audioFeatures[0]['liveness'], audioFeatures[0]['key'], audioFeatures[0]['time_signature'], playlist.loc[index, 'Popularity'], playlist.loc[index, 'Duration']]
            index += 1

    return featureInfo

# Dataframe of playlist features set to global variable
# playlistFeatures = getFeatures(playlistInfo, playlistTrackIds)

# Returns api resonse in JSON format using authorization token given the url including track's id and limit of songs


def createAPIRequest(url):
    # Returns API response in JSON format using authorization 
    # token with the url using the access token
    # Parameters: (url) Spotify GET recommendation url
    # Returns: JSON response of song recommendations

    response = requests.get(
        url,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }
    )
    return response


def getTrackRecommendations(trackIds, limit):
    # Takes track's id and song recommendation limit and returns data frame of song recommendations
    # Parameters: (trackIds, limit) List of Track Ids and how many song recommendations to pull
    # Returns: Dataframe of song recommendations
    recPlaylist = []

    # Dataframe of song recommendations
    recTrackDF = pd.DataFrame(
        columns=("TrackName", "TrackId", "ArtistName", "ArtistId", "Date", "Popularity", "Duration"))
    for indTrack in trackIds:
        recTrack = ""
        numOfRecommendedTracksList = []

        url = f"https://api.spotify.com/v1/recommendations?seed_tracks={indTrack}&limit={limit}"

        # Try and catch as sometimes Spotify API call limit is exceeded causing no JSON song data to be pulled
        try:
            response = createAPIRequest(url)
            response_json = response.json()
            # print(response_json, "\n")
            # print(response_json["tracks"], "\n")
            for track in response_json["tracks"]:
                albumDate = track['album']['release_date']
                # Try and catch as sometimes a track has no release date, if this is the case the year is set to 0000
                try:
                    albumDate = parser.parse(albumDate).year
                except:
                    albumDate == 0000
                popularity = track['popularity']
                duration = track['duration_ms']
                # Sets track's duration from milliseconds to minutes
                duration = int((duration/(1000*60)) % 60)
                recTrack = [track["name"], track["id"], track["artists"]
                            [0]["name"], track["artists"][0]["id"], albumDate, popularity, duration]
                numOfRecommendedTracksList.append(recTrack)
        except:
            time.sleep(1)
            response = createAPIRequest(url)
            print("Error with response: ". response)
            response_json = response.json()
            print(response_json)
            for track in response_json["tracks"]:
                albumDate = track['album']['release_date']
                # Try and catch as sometimes a track has no release date, if this is the case the year is set to 0000
                try:
                    albumDate = parser.parse(albumDate).year
                except:
                    albumDate == 0000
                popularity = track['popularity']
                duration = track['duration_ms']
                # Sets track's duration from milliseconds to minutes
                duration = int((duration/(1000*60)) % 60)
                recTrack = [track["name"], track["id"], track["artists"]
                            [0]["name"], track["artists"][0]["id"], albumDate, popularity, duration]
                numOfRecommendedTracksList.append(recTrack)
        # List of song recommendations for each track are added to a list
        recPlaylist.append(numOfRecommendedTracksList)
    i = 0
    # Song recommendations are then added to dataframe
    for tracks in recPlaylist:
        for indRec in tracks:
            recTrackDF.loc[i] = indRec[0], indRec[1], indRec[2], indRec[3], indRec[4], indRec[5], indRec[6]
            i += 1
    return recTrackDF

# Dataframe of song recommendations are then set to a global variable(the limit of recommended tracks are 5)
#recommendedPlaylist = get_track_recommendations(playlistTrackIds, 5)
# List of song recommendations Track Ids are set to a global variable
#recommendedTrackIds = getSongList(recommendedPlaylist)
# Dataframe of song recommendation's features are set to a global variable
#recommendedFeatures = getFeatures(recommendedPlaylist, recommendedTrackIds)


def getRecommendedFeaturesIntoList(recPlay, playlistLength):
    # Takes data frame of song recommendations and puts all the track's features into a 2D list
    # Parameters: (recPlay) Dataframe of song recommendations
    # Returns: 2D list of song recommendations features
    index = 0
    finalRecommendedList = []
    for i in range(playlistLength):
        recTrackFeaturesList = []
        for k in range(5):
            recTrackFeatures = []
            recTrackFeatures.append(recPlay.loc[index, 'Danceability'])
            recTrackFeatures.append(recPlay.loc[index, 'Energy'])
            recTrackFeatures.append(recPlay.loc[index, 'Loudness'])
            recTrackFeatures.append(recPlay.loc[index, 'Speechiness'])
            recTrackFeatures.append(recPlay.loc[index, 'Acousticness'])
            recTrackFeatures.append(recPlay.loc[index, 'Valence'])
            recTrackFeatures.append(recPlay.loc[index, 'Instrumentalness'])
            recTrackFeatures.append(recPlay.loc[index, 'Tempo'])
            recTrackFeatures.append(recPlay.loc[index, 'Key'])
            recTrackFeatures.append(recPlay.loc[index, 'Liveness'])
            recTrackFeatures.append(recPlay.loc[index, 'TimeSignature'])

            recTrackFeaturesList.append(recTrackFeatures)
            index += 1
        finalRecommendedList.append(recTrackFeaturesList)
    return finalRecommendedList


def getOrignalFeaturesIntoList(orgPlay, playlistLength):
    # Takes data frame of orginal tracks and puts all the track's features into a 2D list
    # Parameters: (orgPlay) Dataframe of orginal tracks
    # Returns: 2D list of orginal track features
    finalOrginalList = []
    for i in range(playlistLength):
        orgPlaylistFeatures = []

        orgPlaylistFeatures.append(orgPlay.loc[i, 'Danceability'])
        orgPlaylistFeatures.append(orgPlay.loc[i, 'Energy'])
        orgPlaylistFeatures.append(orgPlay.loc[i, 'Loudness'])
        orgPlaylistFeatures.append(orgPlay.loc[i, 'Speechiness'])
        orgPlaylistFeatures.append(orgPlay.loc[i, 'Acousticness'])
        orgPlaylistFeatures.append(orgPlay.loc[i, 'Valence'])
        orgPlaylistFeatures.append(orgPlay.loc[i, 'Instrumentalness'])
        orgPlaylistFeatures.append(orgPlay.loc[i, 'Tempo'])
        orgPlaylistFeatures.append(orgPlay.loc[i, 'Key'])
        orgPlaylistFeatures.append(orgPlay.loc[i, 'Liveness'])
        orgPlaylistFeatures.append(orgPlay.loc[i, 'TimeSignature'])

        finalOrginalList.append(orgPlaylistFeatures)

    return finalOrginalList

# Sets list of recommended song's features toa global variable
#listOfRecommendedFeatures = getRecommendedFeaturesIntoList(recommendedFeatures)

# Sets list of orginal song's features toa global variable
#listOfOrgianalFeatures = getOrignalFeaturesIntoList(playlistFeatures)


def knn(orgPlay, recPlay, playlistLength):
    # Takes in orginal playlist and Spotify's recommended playlist, Returns list of song features 
    # calculated by KNearestNeighbor(KNN)
    # Parameters: (orgPlay, recPlay) List of orginal track features and list of recommended track features
    # Returns: list of song features calculated with KNearestNeighbor(KNN)
    knnTrackValuesList = []
    for i in range(playlistLength):
        # Calculates nearestest neighbor for each features using the class NearestNeighbors from sklearn.neighbors
        # NearestNeighbors takes in how many neighbors to return(n_neighbors)
        neighbors = NearestNeighbors(n_neighbors=1)

        # Fit the nearest neighbors estimator from the training dataset
        neighbors.fit(recPlay[i])

        # Find the K-neighbors of a point
        # Returns neigh_dist(Array representing the lengths to points, only present if return_distance=True) 
        # and neigh_ind (Indices of the nearest points in the population matrix)
        neigh_dist, neigh_ind = neighbors.kneighbors([orgPlay[i]])
        knnTrackValuesList.append(recPlay[i][neigh_ind[0][0]])

    return knnTrackValuesList

# Sets list of KNN values to a global variable
#knnList = knn(listOfOrgianalFeatures, listOfRecommendedFeatures)


def getFinalRecommendations(knnValuesList, trackIds, trackFeatures, limit):
    # Creates track recommendations using tracks features calculated with KNN
    # Parameters: (knnValuesList, trackIds, trackFeatures,  limit) List of KNN values for each track, list of orginal Track Ids, dataframe of orignal track's features, recommendation limit of tracks
    # Returns: dataframe of KNN recommendations
    recPlaylist = []
    index = 0
    # Dataframe of song recommendations
    recTrackDF = pd.DataFrame(columns=(
        "TrackName", "TrackId", "ArtistName", "ArtistId", "Date", "Popularity", "Duration"))
    for indTrack in trackIds:
        recTrack = ""
        genreList = trackFeatures.loc[index, 'Genres']
        # Checks if track has a genre
        if(len(genreList) != 0):
            if(genreList[0] != "N/A"):
                genreString = ""
                for i, genre in enumerate(genreList):
                    # Converts list of genre strings to be readable for URL
                    genre = urllib.parse.quote(genre)
                    genreString += genre
                    # Only takes 3 or less genres as the Spotify API GET has a limit of how many it can pull
                    if(i < len(genreList)-1):
                        genreString += "%2C"
                    if(i == 2):
                        break
                # URL to be used if there are genres
                url = f"https://api.spotify.com/v1/recommendations?limit={limit}&seed_tracks={indTrack}&seed_artists={trackFeatures.loc[index,'ArtistId']}&seed_genres={genreString}&target_acousticness={knnValuesList[index][4]}&target_danceability={knnValuesList[index][0]}&target_energy={knnValuesList[index][1]}&target_instrumentalness={knnValuesList[index][6]}&target_liveness={knnValuesList[index][9]}&target_loudness={knnValuesList[index][2]}&target_speechiness={knnValuesList[index][3]}&target_tempo={knnValuesList[index][7]}&target_time_signature={knnValuesList[index][10]}&target_valence={knnValuesList[index][5]}"
            else:
                # URL to be used if there are no genres
                url = f"https://api.spotify.com/v1/recommendations?limit={limit}&seed_tracks={indTrack}&seed_artists={trackFeatures.loc[index,'ArtistId']}&target_acousticness={knnValuesList[index][4]}&target_danceability={knnValuesList[index][0]}&target_energy={knnValuesList[index][1]}&target_instrumentalness={knnValuesList[index][6]}&target_liveness={knnValuesList[index][9]}&target_loudness={knnValuesList[index][2]}&target_speechiness={knnValuesList[index][3]}&target_tempo={knnValuesList[index][7]}&target_time_signature={knnValuesList[index][10]}&target_valence={knnValuesList[index][5]}"
        else:
            # URL to be used if there are no genres
            url = f"https://api.spotify.com/v1/recommendations?limit={limit}&seed_tracks={indTrack}&seed_artists={trackFeatures.loc[index,'ArtistId']}&target_acousticness={knnValuesList[index][4]}&target_danceability={knnValuesList[index][0]}&target_energy={knnValuesList[index][1]}&target_instrumentalness={knnValuesList[index][6]}&target_liveness={knnValuesList[index][9]}&target_loudness={knnValuesList[index][2]}&target_speechiness={knnValuesList[index][3]}&target_tempo={knnValuesList[index][7]}&target_time_signature={knnValuesList[index][10]}&target_valence={knnValuesList[index][5]}"

        index += 1

        # Try and catch as sometimes Spotify API call limit is exceeded causing no JSON song data to be pulled
        try:
            response = createAPIRequest(url)
            response_json = response.json()
            for track in response_json["tracks"]:
                albumDate = track['album']['release_date']
                try:
                    albumDate = parser.parse(albumDate).year
                except:
                    albumDate == 0000
                popularity = track['popularity']
                duration = track['duration_ms']
                # Sets track's duration from milliseconds to minutes
                duration = int((duration/(1000*60)) % 60)
                recTrack = [track["name"], track["id"], track["artists"]
                            [0]["name"], track["artists"][0]["id"], albumDate, popularity, duration]
        except:
            time.sleep(1)
            response = createAPIRequest(url)
            response_json = response.json()
            for track in response_json["tracks"]:
                # Try and catch as sometimes a track has no release date, if this is the case the year is set to 0000
                albumDate = track['album']['release_date']
                try:
                    albumDate = parser.parse(albumDate).year
                except:
                    albumDate == 0000
                duration = track['duration_ms']
                # Sets track's duration from milliseconds to minutes
                duration = int((duration/(1000*60)) % 60)
                popularity = track['popularity']
                recTrack = [track["name"], track["id"], track["artists"]
                            [0]["name"], track["artists"][0]["id"],  albumDate, popularity, duration]

        recPlaylist.append(recTrack)

    i = 0
    for track in recPlaylist:
        recTrackDF.loc[i] = track[0], track[1], track[2], track[3], track[4], track[5], track[6]
        i += 1

    return recTrackDF

def naiveBayes(knnFeaturesSet, length):
    # Creating Naive Bayes Guassian model
    model = GaussianNB()

    # Load data from csv files
    playlistDF = pd.read_csv(
        r'D:/TrackSion/dataset/playlistOfSongs.csv', encoding="ISO-8859-1")
    labelsDF = pd.read_csv(
        r'D:/TrackSion/dataset/labels.csv', encoding="ISO-8859-1")

    # Put loaded data into dataframe
    playlistDF = pd.DataFrame(playlistDF)
    labelsDF = pd.DataFrame(labelsDF)

    # Dropping Track Name and Artist Name from dataframe as they are not needed
    playlistDF = playlistDF.drop(playlistDF.columns[[0, 1]], axis=1)

    # Create an array out of the dataframes with features to keep them as subarrays [[1,2,3],[1,2,3]]
    X = playlistDF.to_numpy()

    # Makes the labes Dataframe into a 1D array
    Y = labelsDF.values.flatten()

    # Ajusts data format to only show year, and makes duration only show minutes without seconds making it into ints
    i = 0
    while i < len(X):
        X[i][0] = parser.parse(X[i][0]).year
        X[i][6] = parser.parse(X[i][6]).hour
        i += 1


    # Puts X into model to launch learing with .fit()
    model.fit(X, Y)
    
    # Checking how succesful the learning was
    model.score(X, Y)

    listOfPredictions = []

    for i in range(length):
        tempList = []
        
        prediction = model.predict([[knnFeaturesSet.loc[i, 'Date'],int(knnFeaturesSet.loc[i, 'Tempo']),int(knnFeaturesSet.loc[i, 'Energy'] * 100),int(knnFeaturesSet.loc[i, 'Danceability']* 100 ),int(knnFeaturesSet.loc[i, 'Loudness']),int(knnFeaturesSet.loc[i, 'Valence']* 100),int(knnFeaturesSet.loc[i, 'Duration']),int(knnFeaturesSet.loc[i, 'Acousticness']* 100),knnFeaturesSet.loc[i, 'Popularity']]])
        print(prediction[0])
        tempList.append(knnFeaturesSet.loc[i, 'TrackName'])
        if(prediction == 1):
            tempList.append("Like")
        else:
            tempList.append("Dislike")
        listOfPredictions.append(tempList)
    
    df = pd.DataFrame(listOfPredictions, columns=["TrackName", "Like/Dislike"])
    pd.DataFrame(df).to_csv('../dataset/nbLikeOrDislike.csv', index=False)
