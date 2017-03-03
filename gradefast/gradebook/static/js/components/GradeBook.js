import * as React from "react";
import * as ReactRedux from "react-redux";

import {actions} from "../actions";
import {store} from "../store";

import Submission from "./Submission";
import HeaderContent from "./HeaderContent";
import SubmissionList from "./SubmissionList";

const GradeBook = React.createClass({
    showList() {
        store.dispatch(actions.setListVisibility(true));
    },

    goToSubmission(submission_id) {
        store.dispatch(actions.goToSubmission(submission_id));
    },

    render() {
        if (this.props.submission_id !== null && !this.props.list_visible) {
            // Show the current submission (includes header)
            return <Submission showListHandler={this.showList} />;
        } else {
            // We don't get an included header, so make one here
            const header = (
                <header>
                    <HeaderContent showScore={false} />
                    <h1>GradeFast</h1>
                </header>
            );

            let section;
            // Show the loading message, if needed
            if (this.props.submission_is_loading) {
                section = <section><h2>Loading...</h2></section>;
            } else if (this.props.list.size) {
                // Show the submission list (showList must be true)
                section = <SubmissionList submissions={this.props.list}
                                          goToSubmissionHandler={this.goToSubmission}/>;
            } else {
                // Tell the user to get their ass moving
                section = (
                    <section>
                        <h2>Start a submission, dammit!</h2>
                        <p className="centered">
                            <a href="https://www.youtube.com/watch?v=oY47hdblMto"
                               title="The Clock Was Tickin'"
                               target="_blank">Clock's a-tickin'</a>.
                        </p>
                        <p className="centered">
                            <a href="https://www.youtube.com/watch?v=Me85PztkYP0"
                               title="Land Locked Blues"
                               target="_blank">The whole world must watch the sad comic display</a>.
                        </p>
                        <p className="centered">
                            <a href="https://www.youtube.com/watch?v=SNX-rQsMRJs"
                               title="Noah's Worst Nightmare"
                               target="_blank">It's a great time to be alive</a>.
                        </p>
                    </section>
                );
            }
            return (
                <div className="container">
                    {header}
                    {section}
                </div>
            );
        }
    }
});

function mapStateToProps(state) {
    return {
        submission_id: state.get("submission_id"),
        list_visible: state.get("list_visible"),
        list: state.get("list"),
        submission_is_loading: state.get("submission_is_loading")
    };
}

export default ReactRedux.connect(mapStateToProps)(GradeBook);
