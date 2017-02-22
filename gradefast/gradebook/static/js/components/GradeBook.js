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

    goToSubmission(index) {
        store.dispatch(actions.goToSubmission(index));
    },

    render() {
        let header, section;
        if (this.props.submissionIndex !== null && !this.props.showList) {
            // Show the current submission (includes header)
            section = <Submission showListHandler={this.showList} />;
        } else {
            // We don't get an included header, so make one here
            header = (
                <header>
                    <HeaderContent showScore={false} />
                    <h1>GradeFast</h1>
                </header>
            );
            // Show the loading message, if needed
            if (this.props.submissionIsLoading) {
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
                        <p className="centered"><a href="https://www.youtube.com/watch?v=oY47hdblMto" target="_blank">Clock's a-tickin'</a></p>
                    </section>
                );
            }
        }
        return (
            <div>
                {header}
                {section}
            </div>
        );
    }
});

function mapStateToProps(state) {
    return {
        submissionIndex: state.get("submission_index"),
        showList: state.get("list_visible"),
        list: state.get("list"),
        submissionIsLoading: state.get("submission_is_loading")
    };
}

export default ReactRedux.connect(mapStateToProps)(GradeBook);
