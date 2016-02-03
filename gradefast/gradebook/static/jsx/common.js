/**
 * Report an HTTP request error.
 * @param {boolean} completed - Whether the request actually completed.
 * @param {string} path - The path that the request was going to.
 * @param {string} status - The HTTP status, if any.
 * @param {string} [details] - Any details, such as the response body.
 * @param {Event} [event] - An error or event object to log.
 */
function reportError(completed, path, status, details, event) {
    var pre;
    if (completed) {
        pre = `Invalid response from ${path} (status: ${status})`;
    } else {
        pre = `Request to ${path} was not successful (status: ${status})`;
    }
    console.log(pre, details, event);
    alert(pre + (details ? `:\n\n${details}` : `.`));
}

var HeaderContent = React.createClass({
    render() {
        var score;
        if (this.props.showScore) {
            score = <span>
                <label>Current Score: </label>{this.props.currentScore}&nbsp;/&nbsp;{this.props.maxScore}
                &emsp;
                <input id="late" type="checkbox" ref="late" onChange={(event) => {
                    this.props.setLate(this.refs.late.checked)
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

var SubmissionList = React.createClass({
    render() {
        return (
            <section>
                <h2>Submissions</h2>
                <ul>
                    {
                        this.props.submissions.filter((item) => {
                            return !!item;
                        }).map((item, index) => {
                            return <li>
                                <a href="#" onClick={(event) => {
                                    event.preventDefault();
                                    this.props.goToSubmission(index);
                                }}>{index}: <strong>{item.name}</strong></a>
                            </li>;
                        })
                    }
                </ul>
            </section>
        );
    }
});
