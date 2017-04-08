import * as React from "react";

import {actions} from "../actions";
import {store} from "../store";

const SubmissionList = ({submissions}) => {
    return (
        <div>
            <ul className="submission-list">
                {
                    submissions.filter((submission) => {
                        return !!submission;
                    }).map((submission) => {
                        const handleClick = (event) => {
                            event.preventDefault();
                            store.dispatch(actions.goToSubmission(submission.get("id")));
                        };
                        return (
                            <li key={submission.get("id")}>
                                <a href="#poundsign" onClick={handleClick}>
                                    ({submission.get("id")}) <strong>{submission.get("name")}</strong>
                                </a>
                                <label>
                                    &nbsp;&nbsp;
                                    {submission.get("current_score")} / {submission.get("max_score")}
                                    {submission.get("is_late") ? <em>&nbsp;&nbsp;(late)</em> : undefined}
                                </label>
                            </li>
                        );
                    })
                }
            </ul>
        </div>
    );
};

export default SubmissionList;
