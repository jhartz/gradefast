import * as React from "react";

import {actions} from "../actions";
import {store} from "../store";

const SubmissionList = React.createClass({
    handleItemClick(submission_id, event) {
        event.preventDefault();
        store.dispatch(actions.goToSubmission(submission_id));
    },

    render() {
        return (
            <div>
                <ul>
                    {
                        this.props.submissions.filter((submission) => {
                            return !!submission;
                        }).map((submission) => {
                            return (
                                <li key={submission.id}>
                                    <a href="#" onClick={this.handleItemClick.bind(submission.id)}>
                                        {submission.id}: <strong>{submission.name}</strong>
                                    </a>
                                </li>
                            );
                        })
                    }
                </ul>
            </div>
        );
    }
});

export default SubmissionList;
