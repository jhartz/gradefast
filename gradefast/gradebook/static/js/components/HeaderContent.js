import * as React from "react";

export default React.createClass({
    render() {
        let score;
        if (this.props.showScore) {
            score = <span>
                <label>Current Score: </label>{this.props.currentScore}&nbsp;/&nbsp;{this.props.maxScore}
                &emsp;
                <input id="late" type="checkbox" ref="late" onChange={(event) => {
                    this.props.setLateHandler(this.refs.late.checked)
                }} /><label htmlFor="late"> Late?</label>
                &emsp;
            </span>;
        }

        return (
            <h2><span>
                {score}
                <a href={`${CONFIG.BASE}grades.csv`} title="Download Grades as CSV"
                   target="_blank"><img src={`${CONFIG.STYLE_BASE}csv.png`} /></a>
                <a href={`${CONFIG.BASE}grades.json`} title="Download Grades as JSON"
                   target="_blank"><img src={`${CONFIG.STYLE_BASE}json.png`} /></a>
            </span></h2>
        );
    }
});
