import * as Immutable from "immutable";
import * as React from "react";
import * as ReactRedux from "react-redux";

import {actions} from "../actions";
import {store} from "../store";

import CommentsTextarea from "./utils/CommentsTextarea";
import RandomSong from "./utils/RandomSong";

import GradeList from "./GradeList";
import Header from "./Header";
import SubmissionList from "./SubmissionList";

const GradeBook = React.createClass({
    handleOverallCommentsChange(value) {
        store.dispatch(actions.setOverallComments(value));
    },

    render() {
        let pageTitle = "GradeFast";
        let showScore = false;

        let headerContent;
        let sectionContent;
        let footerContent;

        if (this.props.loading) {
            // Loading message
            sectionContent = <h2>Loading...</h2>;

        } else if (this.props.list_visible) {
            // List of submissions
            headerContent = <span>Submissions</span>;
            sectionContent = <SubmissionList submissions={this.props.list}/>;

        } else if (this.props.submission_id !== null) {
            // An actual submission! It's almost like this is what we're actually here for
            pageTitle = this.props.submission_id + ": " + this.props.submission_name + " - GradeFast";
            showScore = true;

            headerContent = (
                <span>
                    {this.props.submission_id}: <em>{this.props.submission_name || "no-name"}</em>
                </span>
            );
            sectionContent = <GradeList path={Immutable.List()} grades={this.props.grades} />;
            footerContent = (
                <CommentsTextarea onChange={this.handleOverallCommentsChange}
                                  placeholder="Overall Comments (Markdown-parsed)"
                                  value={this.props.overall_comments}
                                  valueHTML={this.props.overall_comments
                                      .replace(/&/g, "&amp;").replace(/"/g, "&quot;")
                                      .replace(/</g, "&lt;").replace(/>/g, "&gt;")
                                      .replace(/\n/g, "<br />")
                                      + '<br /><small>TODO: Render markdown</small>'}
                                  minRows={3}
                                  maxHeightPx={() => Math.round(document.documentElement.clientHeight * 0.25)}
                />
            );

        } else {
            // Tell the user to get their ass moving
            sectionContent = this.getInspiration();
        }

        if (!headerContent) {
            headerContent = <span>GradeFast</span>
        }
        if (!footerContent) {
            footerContent = <div style={{textAlign: "right"}}><RandomSong /></div>;
        }

        // XXX: It feels a bit hacky to update the document title here...
        document.title = pageTitle;

        return (
            <div className="container">
                <Header showScore={showScore}>{headerContent}</Header>
                <section>{sectionContent}</section>
                <footer>{footerContent}</footer>
            </div>
        );
    },

    getInspiration() {
        return (
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
});

function mapStateToProps(state) {
    return {
        loading: state.get("loading"),

        list_visible: state.get("list_visible"),
        list: state.get("list"),

        submission_id: state.get("submission_id"),
        submission_name: state.get("submission_name"),
        overall_comments: state.get("submission_overall_comments"),
        grades: state.get("submission_grades")
    };
}

export default ReactRedux.connect(mapStateToProps)(GradeBook);
