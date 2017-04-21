import * as React from "react";

import {actions} from "../actions";
import {store} from "../store";

const SubmissionList = ({submissions, data_key}) => {
    return (
        <div>
            <table className="submission-list"><tbody>
                {
                    submissions.filter((submission) => {
                        return !!submission;
                    }).map((submission) => {
                        const handleClick = (event) => {
                            event.preventDefault();
                            store.dispatch(actions.goToSubmission(submission.get("id")));
                        };

                        const end_tds = [];
                        if (submission.get("has_log")) {
                            const logBase = CONFIG.BASE + "log/" + encodeURIComponent(submission.get("id"));
                            const logParams = "data_key=" + encodeURIComponent(data_key);
                            end_tds.push(
                                <td key={"CONDUCTOR"}>
                                    <a href={`${logBase}.html?${logParams}`} target="_blank">log</a>
                                </td>
                            );
                            end_tds.push(
                                <td key={"CABOOSE"}>
                                    <a href={`${logBase}.txt?${logParams}`} target="_blank">text log</a>
                                </td>
                            );
                        }

                        return (
                            <tr key={submission.get("id")}
                                title={submission.get("full_name") + " (" + submission.get("path") + ")"}>
                                <td>
                                    <label>({submission.get("id")})</label>
                                </td>
                                <td>
                                    <a href="#poundsign" onClick={handleClick}>
                                        <strong>{submission.get("name")}</strong>
                                    </a>
                                </td>
                                <td>
                                    <label>
                                        {submission.get("current_score")}
                                    </label>
                                </td>
                                <td style={{paddingLeft: "0"}}>
                                    <label>
                                        / {submission.get("max_score")}
                                        {submission.get("is_late") ? <em>&nbsp;&nbsp;(late)</em> : undefined}
                                    </label>
                                </td>
                                {end_tds}
                            </tr>
                        );
                    })
                }
            </tbody></table>
        </div>
    );
};

export default SubmissionList;
