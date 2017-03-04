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

// These songs are used for the song snippet at the top of the gradebook.

// I welcome PR's for more songs here!
// Pick one of your favorite songs, and choose a line or 2 from the lyrics.

// Only rule is: no more than one song per artist. (Make sure to put the
// artist in a comment so future people know that that artist is out.)

// The snippet can be from any part of the song; in fact, it is encouraged
// to take it from some part of the song that most people won't recognize!

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
    }
];

// A bit of history: Why does GradeFast include a random song at the top of
// the gradebook interface? Well, there's a CSS property in the stylesheet
// that puts a border at the top of each grade section and each grade score,
// and I didn't feel like making a special rule to not put a border above the
// first one. So, I put a song link there!

// Maybe someday I'll add a "grading background music" feature to GradeFast
// that will use these songs to play background music while you grade.
// But, probably not :P
