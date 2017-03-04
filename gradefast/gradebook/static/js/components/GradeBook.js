import * as React from "react";
import * as ReactRedux from "react-redux";

import {actions} from "../actions";
import {store} from "../store";

import Header from "./Header";
import Submission from "./Submission";
import SubmissionList from "./SubmissionList";

const GradeBook = React.createClass({
    showList() {
        store.dispatch(actions.setListVisibility(true));
    },

    goToSubmission(submission_id) {
        store.dispatch(actions.goToSubmission(submission_id));
    },

    render() {
        // XXX: It's probably not a good idea to set "document.title" here...

        if (this.props.submission_id !== null && !this.props.list_visible) {
            document.title = this.props.submission_name + " - GradeFast";

            // Show the current submission (this includes div.container with header/section/footer)
            return <Submission showListHandler={this.showList} />;
        } else {
            document.title = "GradeFast";

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
                    <Header showScore={false}>
                        <h1>GradeFast</h1>
                    </Header>
                    {section}
                </div>
            );
        }
    }
});

function mapStateToProps(state) {
    return {
        submission_id: state.get("submission_id"),
        submission_name: state.get("submission_name"),
        list_visible: state.get("list_visible"),
        list: state.get("list"),
        submission_is_loading: state.get("submission_is_loading")
    };
}

export default ReactRedux.connect(mapStateToProps)(GradeBook);
