import React, { Component } from "react";
import "./App.css";
import Spotify from "spotify-web-api-node";
import logo from "./TrackSionLogo.png";

const spotifyWebApi = new Spotify();
var playlist = "";
var Talk = require("./Talk.js");
var passJSON = Talk.passJSON;
var recTracks = "";
var newPlaylistId = "";
var trackUris = [];

//Gets essential track attributes and sets up in JSON format
var JSONplaylistFunction = function (body) {
  var playlist_JSON = {};
  var newTracks = [];
  var i;
  var playlistSize = body.tracks.total;

  if (playlistSize > 50) {
    playlistSize = 50;
  }
  for (i = 0; i < playlistSize; i++) {
    var trackId = body.tracks.items[i].track.id;
    var trackName = body.tracks.items[i].track.name;
    var artistId = body.tracks.items[i].track.album.artists[0].id;
    var artistName = body.tracks.items[i].track.album.artists[0].name;
    var duration = body.tracks.items[i].track.duration_ms;
    var popularity = body.tracks.items[i].track.popularity;
    var date = body.tracks.items[i].track.album.release_date;
    newTracks.push({
      trackId: trackId,
      trackName: trackName,
      artistId: artistId,
      artistName: artistName,
      duration: duration,
      popularity: popularity,
      date: date,
    });
  }
  playlist_JSON.newTracks = newTracks;
  
  return playlist_JSON;
};

class App extends Component {
  constructor() {
    super();
    const params = this.getHashParams();
    this.state = {
      loggedIn: params.access_token ? true : false,
      playlists: {
        playlists: [],
      },
      tracks: {
        tracks: [],
      },
      recommendedTrackIds: {
        recommendedTrackIds: [],
      },
    };
    if (params.access_token) {
      spotifyWebApi.setAccessToken(params.access_token);
    }
  }
  //Takes authorization token from redirect url
  getHashParams() {
    var hashParams = {};
    var e,
      r = /([^&;=]+)=?([^&;]*)/g,
      q = window.location.hash.substring(1);
    while ((e = r.exec(q))) {
      hashParams[e[1]] = decodeURIComponent(e[2]);
    }
    return hashParams;
  }

  //Gets User's playlists
  getUserPlaylists() { 
    spotifyWebApi.getUserPlaylists({ limit: 50 }).then((response) => {
      this.setState({
        playlists: {
          playlists: response.body.items,
        },
      });
    });
  }
  //Set state of recommended tracks
  getRecTracks() {
    console.log(spotifyWebApi.getRefreshToken());
    spotifyWebApi.getTracks(recTracks).then((response) => {
      console.log(response);
      this.setState({
        recommendedTrackIds: {
          recommendedTrackIds: response.body.tracks,
        },
      });
    });
  }

  //Gets selected playlist from drop down list
  getSelectValue() {
    var selectedValue = document.getElementById("selectplaylist").value;
    console.log(selectedValue);
    playlist = "";
    this.state.playlists.playlists.forEach(function (value) {
      if (selectedValue === value.name) {
        playlist = value.id;
        console.log("Found it", playlist);
      }
    });
    recTracks = "";
    selectedValue = null;
    spotifyWebApi.getPlaylist(playlist,).then(
      function (data) {
        console.log("Sending playlist to python", data.body);

        passJSON(JSONplaylistFunction(data.body)).then((response) => {
          recTracks = response;

          alert("Recommendations Complete");
          console.log("Recieved playlist from python", recTracks);
        });
      },
      function (err) {
        console.log("Something went wrong!", err);
      }
    );
  }

  //Add playlist to Spotify library
  addToLibrary() {
    newPlaylistId = "";
    trackUris = [];
    this.state.recommendedTrackIds.recommendedTrackIds.forEach(function (
      value
    ) {
      trackUris.push(value.uri);
    });
    console.log("Track uris: ", trackUris);
    spotifyWebApi
      .createPlaylist("TrackSion Recommended Playlist", {
        public: true,
      })
      .then(
        function (data) {
          newPlaylistId = data.body.id;
          console.log("Created playlist!", trackUris);
          spotifyWebApi.addTracksToPlaylist(newPlaylistId, trackUris).then(
            function (data) {
              console.log("Added tracks to playlist!");
            },
            function (err) {
              console.log("Something went wrong!", err);
            }
          );
        },
        function (err) {
          console.log("Something went wrong!", err);
        }
      );
  }

  render() {
    return (
      <div className="App">
        <nav class="navbar">
          <div class="navbar_container">
            <img src={logo} alt="Logo" />
            <div class="navbar__toggle" id="mobile-menu">
              <span class="bar"></span>
            </div>
            <ul class="navbar__menu">
              <li class="navbar__btn">
                <a href="http://localhost:8888/login" class="button">
                  Login With Spotify
                </a>
              </li>
            </ul>
          </div>
        </nav>
        <body>
          <div>
            <button class="button"onClick={() => this.getUserPlaylists()}>
              Get Playlists
            </button>
            <br></br>
            <section>
              Please keep in mind that it will only take the first 50 tracks due
              to API limitations
            </section>
          </div>
          <div>
            <select id="selectplaylist" onchange="getSelectValue();">
              {this.state.playlists.playlists.map((playlist, idx) => (
                <option key={idx} value={playlist.items}>
                  {playlist.name}
                </option>
              ))}
            </select>
          </div>
          <button  class="button" onClick={() => this.getSelectValue()}>Playlist Select</button>
          <section>
            <br></br>
              Please wait untill screen alerts you that the playlist 
              is ready before selecting Show Me My Recommendations
            </section>
          <br></br>
          <button  class="button" onClick={() => this.getRecTracks()}>
            Show Me My Recommendations
          </button>
          <br></br>
          <button  class="button" onClick={() => this.addToLibrary()}>
            Add To Spotify Library
          </button>
        </body>
        <br></br>
        <table class="styled-table">
          <thead>
            <tr>
              <th>Track Name</th>
              <th>Artist</th>
              <th>Album Cover</th>
            </tr>
          </thead>
          <tbody>
            {this.state.recommendedTrackIds.recommendedTrackIds.map(
              (tracks, key) => {
                return (
                  <tr key={key}>
                    <td>{tracks.name}</td>
                    <td>{tracks.artists[0].name} </td>
                    <td>
                      <img
                        src={tracks.album.images[0].url}
                        style={{ width: 100 }}
                      />
                    </td>
                  </tr>
                );
              }
            )}
          </tbody>
        </table>
        <footer>
          Any issues please contact at: tracksionContact@gmail.com
        </footer>
      </div>
    );
  }
}

export default App;
