import * as React from "react";

import {SONGS} from "../../SONGS";

export default () => {
    const song = SONGS[Math.floor(Math.random() * SONGS.length)];
    return (
        <a href={song.link} target="_blank">{song.snippet}</a>
    );
};
