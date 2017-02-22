import * as React from "react";

export default ({submissions, goToSubmissionHandler}) => (
    <section>
        <h2>Submissions</h2>
        <ul>
            {
                submissions.filter((item) => {
                    return !!item;
                }).map((item, index) => {
                    return <li>
                        <a href="#" onClick={(event) => {
                            event.preventDefault();
                            goToSubmissionHandler(index);
                        }}>{index}: <strong>{item.name}</strong></a>
                    </li>;
                })
            }
        </ul>
    </section>
);
