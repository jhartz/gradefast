export default React.createClass({
    render() {
        var score;
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
                <a href={`${base}grades.csv`} title="Download Grades as CSV"
                   target="_blank"><img src={`${styleBase}csv.png`} /></a>
                <a href={`${base}grades.json`} title="Download Grades as JSON"
                   target="_blank"><img src={`${styleBase}json.png`} /></a>
            </span></h2>
        );
    }
});
