import * as React from "react";
import * as ReactRedux from "react-redux";

import {actions} from "../actions";
import {store} from "../store";

function formatTime(seconds) {
    let hours = Math.floor(seconds / 3600);
    seconds -= hours * 3600;

    let minutes = Math.floor(seconds / 60);
    seconds -= minutes * 60;

    seconds = Math.round(seconds);
    if (seconds < 10) {
        seconds = "0" + seconds;
    }

    if (hours > 0) {
        if (minutes < 10) {
            minutes = "0" + minutes;
        }
        return `${hours}:${minutes}:${seconds}`;
    } else {
        return `${minutes}:${seconds}`;
    }
}

function formatPercent(percent) {
    // This is just chock full of floating point sins...

    percent = Math.round(percent * 10) / 10;
    const intPart = Math.floor(percent);
    const decPart = percent - intPart;

    return `${intPart}.${Math.round(decPart * 10)}%`;
}

const SubmissionList = React.createClass({
    renderStats(stats, formatterFunc, titleLabel) {
        return (
            <table className="stats-list"><tbody>
                {
                    [
                        ["Minimum:", "min"],
                        ["Maximum:", "max"],
                        ["Median:", "median"]
                    ].map(([title, prop], index) => {
                        if (stats.has(prop) && stats.get(prop) !== null) {
                            const value = stats.get(prop);
                            return (
                                <tr key={index}>
                                    <th>{title}</th>
                                    <td className="stats-number" title={value.get(0) + titleLabel}>
                                        {formatterFunc(value.get(0))}
                                    </td>
                                    <td>
                                        {
                                            value.get(1).map((submission_id, index) => {
                                                const submission = this.props.submissions.get(submission_id);
                                                if (submission) {
                                                    const handleClick = (event) => {
                                                        event.preventDefault();
                                                        store.dispatch(actions.goToSubmission(submission_id));
                                                    };
                                                    return (
                                                        <span key={index}>
                                                            {index > 0 ? ", " : ""}
                                                            <a href="#poundsign"
                                                               onClick={handleClick}
                                                               title={`(${submission_id}) ${submission.get("full_name")}`}>
                                                                {submission.get("name")}
                                                            </a>
                                                        </span>
                                                    );
                                                } else {
                                                    return (
                                                        <span key={index}>
                                                            {index > 0 ? ", " : ""}
                                                            <span>
                                                                Unknown submission {submission_id}
                                                            </span>
                                                        </span>
                                                    );
                                                }
                                            })
                                        }
                                    </td>
                                </tr>
                            );
                        }
                    })
                }
                {
                    [
                        ["Average:", "mean"],
                        ["Standard Deviation:", "std_dev"]
                    ].map(([title, prop], index) => {
                        if (stats.has(prop) && stats.get(prop) !== null) {
                            const value = stats.get(prop);
                            return (
                                <tr key={index}>
                                    <th>{title}</th>
                                    <td className="stats-number" title={value + titleLabel}>
                                        {formatterFunc(value)}
                                    </td>
                                </tr>
                            );
                        }
                    })
                }
                {
                    (!stats.has("modes") || stats.get("modes").size === 0) ? undefined :
                    <tr>
                        <th>Mode:</th>
                        <td className="stats-number">
                            {
                                stats.get("modes").map((value, index) => {
                                    return (
                                        <span key={index} title={value + titleLabel}>
                                            {formatterFunc(value)}<br />
                                        </span>
                                    );
                                })
                            }
                        </td>
                    </tr>
                }
            </tbody></table>
        );
    },

    render() {
        return (
            <div>
                <table className="submission-list">
                    <tbody>
                    {
                        this.props.submissions.valueSeq().map((submission) => {
                            const handleClick = (event) => {
                                event.preventDefault();
                                store.dispatch(actions.goToSubmission(submission.get("id")));
                            };

                            const end_tds = [];
                            if (submission.get("has_logs")) {
                                const logBase = CONFIG.BASE + "log/" + encodeURIComponent(submission.get("id"));
                                const logParams = "data_key=" + encodeURIComponent(this.props.data_key);
                                end_tds.push(
                                    <td key={"CONDUCTOR"}>
                                        <a href={`${logBase}.html?${logParams}`}
                                           target="_blank">log</a>
                                    </td>
                                );
                                end_tds.push(
                                    <td key={"CABOOSE"}>
                                        <a href={`${logBase}.txt?${logParams}`} target="_blank">text log</a>
                                    </td>
                                );
                            }

                            const total_time = submission.get("times").reduce((a, b) => a + b.get(1) - b.get(0), 0);
                            if (total_time > 0) {
                                end_tds.push(
                                    <td key={"TIMES"} title={total_time + " sec"}>
                                        Grading Time: {formatTime(total_time)}
                                    </td>
                                );
                            }

                            const percentage = 100 * submission.get("points_earned") / submission.get("points_possible");
                            return (
                                <tr key={submission.get("id")}
                                    title={submission.get("full_name") + " (" + submission.get("path") + ")"}>
                                    <td>
                                        ({submission.get("id")})
                                    </td>
                                    <td>
                                        <a href="#poundsign" onClick={handleClick}>
                                            <strong>{submission.get("name")}</strong>
                                        </a>
                                        {submission.get("is_late") ?
                                            <em>&nbsp;&nbsp;(late)</em> : undefined}
                                    </td>
                                    <td>
                                        {submission.get("points_earned")}
                                    </td>
                                    <td style={{paddingLeft: "0"}}>
                                        / {submission.get("points_possible")}
                                    </td>
                                    <td title={percentage + "%"}>
                                        ({formatPercent(percentage)})
                                    </td>
                                    {end_tds}
                                </tr>
                            );
                        })
                    }
                    </tbody>
                </table>

                <h3 className="centered">Grade Statistics</h3>
                {this.renderStats(this.props.grading_stats, formatPercent, "%")}

                <h3 className="centered">Grading Time Statistics</h3>
                {this.renderStats(this.props.timing_stats, formatTime, " sec")}
            </div>
        );
    }
});

function mapStateToProps(state) {
    return {
        data_key: state.get("data_key"),

        submissions: state.get("submissions"),
        grading_stats: state.get("grading_stats"),
        timing_stats: state.get("timing_stats")
    };
}

export default ReactRedux.connect(mapStateToProps)(SubmissionList);
