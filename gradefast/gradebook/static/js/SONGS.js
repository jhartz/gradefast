import * as React from "react";

/*************************************************************************************************

                            _______
                            \  ___ `'.         __.....__
  .--./)                     ' |--.\  \    .-''         '.        _.._
 /.''\\   .-,.--.            | |    \  '  /     .-''"'-.  `.    .' .._|                       .|
| |  | |  |  .-. |    __     | |     |  '/     /________\   \   | '       __                .' |_
 \`-' /   | |  | | .:--.'.   | |     |  ||                  | __| |__  .:--.'.         _  .'     |
 /("'`    | |  | |/ |   \ |  | |     ' .'\    .-------------'|__   __|/ |   \ |      .' |'--.  .-'
 \ '---.  | |  '- `" __ | |  | |___.' /'  \    '-.____...---.   | |   `" __ | |     .   | / |  |
  /'""'.\ | |      .'.''| | /_______.'/    `.             .'    | |    .'.''| |   .'.'| |// |  |
 ||     ||| |     / /   | |_\_______|/       `''-...... -'      | |   / /   | |_.'.'.-'  /  |  '.'
 \'. __// |_|     \ \._,\ '/                                    | |   \ \._,\ '/.'   \_.'   |   /
  `'---'           `--'  `"                                     |_|    `--'  `"             `'-'


               _____                      __    _ __
              / ___/____  ____  ____ _   / /   (_) /_  _________ ________  __
              \__ \/ __ \/ __ \/ __ `/  / /   / / __ \/ ___/ __ `/ ___/ / / /
             ___/ / /_/ / / / / /_/ /  / /___/ / /_/ / /  / /_/ / /  / /_/ /
            /____/\____/_/ /_/\__, /  /_____/_/_.___/_/   \__,_/_/   \__, /
                             /____/                                 /____/

*************************************************************************************************/

// These songs are used for the song snippet in the gradebook footer

// I welcome PR's for more songs here! Pick one of your favorite songs, and choose a line or 2 from
// the lyrics to use as a snippet.
// (It would be nice if the PR also included an actual contribution to GradeFast :p)

// Only rule is: no more than one song per artist. (Make sure to put the artist in a comment so
// future people know that that artist is out.)

// The snippet can be from any part of the song; in fact, it is encouraged to take it from some
// part of the song that most people won't recognize!

export const SONGS = [
    {
        // Billy Joel
        snippet: "They sit at the bar and put bread in my jar; And say, \"Man, what are you doing here?\"",
        link: "https://www.youtube.com/watch?v=gxEPV4kolz0"
    },
    {
        // Billy Joel
        snippet: "And a couple of paintings from Sears",
        link: "https://www.youtube.com/watch?v=JUz48xw_OiM"
    },
    {
        // Tracy Chapman / Jonas Blue
        snippet: "Maybe we make a deal",
        link: "https://www.youtube.com/watch?v=X6qIvzeNPxk"
    },
    {
        // Nena
        snippet: "Hielten sich für schlaue Leute",
        link: "https://www.youtube.com/watch?v=ZLIn0JNC57c"
    },
    {
        // Goldfinger
        snippet: "Dass es einmal soweit kommt, Wegen 99 Luftballons",
        link: "https://www.youtube.com/watch?v=JQFplXS0DIM"
    },
    {
        // Pentatonix
        snippet: "Love is not a victory march",
        link: "https://www.youtube.com/watch?v=LRP8d7hhpoQ"
    },
    {
        // John Denver
        snippet: "Misty taste of moonshine; Teardrops in my eye",
        link: "https://www.youtube.com/watch?v=1vrEljMfXYo"
    },
    {
        // Margot and the Nuclear So-and-Sos
        snippet: "Satan, settle down! Keep your trousers on",
        link: "https://www.youtube.com/watch?v=Vm3LE0eX9aY"
    },
    {
        // Car Seat Headrest
        snippet: "It's not a race at all",
        link: "https://www.youtube.com/watch?v=ccztRby3FAk"
    },
    {
        // David Bowie
        snippet: "Can you hear me, Major Tom?",
        link: "https://www.youtube.com/watch?v=iYYRH4apXDo"
    },
    {
        // Beck
        snippet: <span>
            Got a couple of couches, sleep on the love seat.<br />
            Someone keeps saying' I'm insane to complain, about a shotgun wedding and a stain on my shirt.<br />
            Don't believe everything that you breathe; you get a parking violation and a maggot on your sleeve.<br />
            So shave your face, with some mace in the dark;<br />
            Saving' all your food stamps, and burning' down the trailer park.<br />
            Yo. ... Cut it.
        </span>,
        link: "https://www.youtube.com/watch?v=6xHh8bSX-zc"
    },
    {
        // In This Moment
        snippet: "I heard I don't belong in this scene; Sex Metal Barbie, Homicidal Queen",
        link: "https://www.youtube.com/watch?v=vzFUESHaDJk"
    },
    {
        // Halestorm
        snippet: "Let's toast 'cause things got better",
        link: "https://www.youtube.com/watch?v=pdEmsYOOQjU"
    },
    {
        // The Kingston Trio
        // (some good Boston culture here)
        snippet: <span>
            Get poor Charlie off the&nbsp;
            <abbr title="Metropolitan Transit Authority (predecessor to the MBTA)">M.T.A.</abbr>
        </span>,
        link: "https://www.youtube.com/watch?v=S7Jw_v3F_Q0"
    },
    {
        // Silverson Pickups
        snippet: "Made of our cozy decomposing wires",
        link: "https://www.youtube.com/watch?v=kL2r82X0SCI"
    },
    {
        // Imogen Heap
        snippet: "Trains and sewing machines",
        link: "https://www.youtube.com/watch?v=McDgDlnDX0Y"
    },
    {
        // Noah and the Whale
        snippet: "Some people wear their history like a map on their face",
        link: "https://www.youtube.com/watch?v=JE4-5kDHFUE"
    },
    {
        // Conor Oberst
        snippet: "Life's an odd job that she don't got the nerve to quit",
        link: "https://www.youtube.com/watch?v=Y_Cy2pxqCRo"
    },
    {
        // Bright Eyes
        snippet: <span>
            And she looks at the man and says "Where are we going?" and he looks at her and he says "We're going to a party.<br />
            It's a birthday party. It's your birthday party.<br />
            Happy birthday darling. We love you very, very, very, very, very, very, very much.
        </span>,
        link: "https://www.youtube.com/watch?v=qikRcAiCtKM"
    },
    {
        // Dolly Parton
        // (I first heard this one on 8-track)
        snippet: <span>
            While standin' here on the edge of this bridge,<br />
            Lookin' down I see:<br />
            The face of Joe and Gypsy, lookin' up at me
        </span>,
        link: "https://www.youtube.com/watch?v=_AVv9Yg1XL0"
    },
];
