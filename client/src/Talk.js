const axios = require("axios");

async function passJSON(JSONdata) {
  let res = await axios.post('http://127.0.0.1:5000/getPlaylistJSON', JSONdata );
  
  console.log("Sending back to JavaScript",  res.data)
  return await  res.data
}

module.exports = { passJSON };