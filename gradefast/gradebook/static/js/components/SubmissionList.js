import * as React from "react";

export default ({submissions, goToSubmissionHandler}) => (
    <section>
        <h2>Submissions</h2>
        <ul>
            {
                submissions.filter((submission) => {
                    return !!submission;
                }).map((submission) => {
                    return <li key={submission.id}>
                        <a href="#" onClick={(event) => {
                            event.preventDefault();
                            goToSubmissionHandler(submission.id);
                        }}>{submission.id}: <strong>{submission.name}</strong></a>
                    </li>;
                })
            }
        </ul>
    </section>
);
