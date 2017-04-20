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
                        const logHref = CONFIG.BASE + "log/" + encodeURIComponent(submission.get("id")) +
                            "?data_key=" + encodeURIComponent(data_key);
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
                                        {submission.get("current_score")} / {submission.get("max_score")}
                                        {submission.get("is_late") ? <em>&nbsp;&nbsp;(late)</em> : undefined}
                                    </label>
                                </td>
                                {submission.get("has_log")
                                    ? <td>
                                        <a href={logHref} target="_blank">log</a>
                                      </td>
                                    : undefined}
                            </tr>
                        );
                    })
                }
            </tbody></table>
        </div>
    );
};

export default SubmissionList;
