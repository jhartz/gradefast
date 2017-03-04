import * as React from "react";

export default ({showScore, currentScore, maxScore, onSetLate, children}) => {
    let score;
    if (showScore) {
        score = <span>
            <label>Current Score: </label>{currentScore}&nbsp;/&nbsp;{maxScore}
            &emsp;
            <input id="late"
                   type="checkbox"
                   onChange={(event) => onSetLate(event.target.checked)}
            /><label htmlFor="late"> Late?</label>
            &emsp;
        </span>;
    }

    return (
        <header>
            <h2><span>
                {score}
                <a href={`${CONFIG.BASE}grades.csv`} title="Download Grades as CSV"
                   target="_blank"><img src={`${CONFIG.STYLE_BASE}csv.png`} /></a>
                <a href={`${CONFIG.BASE}grades.json`} title="Download Grades as JSON"
                   target="_blank"><img src={`${CONFIG.STYLE_BASE}json.png`} /></a>
            </span></h2>
            {children}
        </header>
    );
};
