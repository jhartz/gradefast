import * as Immutable from "immutable";
import * as React from "react";
import * as ReactRedux from "react-redux";

import {actions} from "../actions";
import {store} from "../store";

import CommentsTextarea from "./CommentsTextarea";
import HeaderContent from "./HeaderContent";
import GradeList from "./GradeList";

const Submission = React.createClass({
    handleOverallCommentsChange(value) {
        store.dispatch(actions.setOverallComments(value));
    },

    setLate(isLate) {
        store.dispatch(actions.setLate(isLate));
    },

    render() {
        return (
            <div className="container">
                <header>
                    <HeaderContent showScore={true}
                                   currentScore={this.props.current_score}
                                   maxScore={this.props.max_score}
                                   isLate={this.props.is_late}
                                   setLateHandler={this.setLate} />
                    <h1><a href="#" onClick={(event) => {
                        event.preventDefault();
                        this.props.showListHandler();
                    }}>{this.props.submission_id}: {this.props.name || "GradeFast"}</a></h1>
                </header>
                <section>
                    <GradeList path={Immutable.List()} grades={this.props.grades} />
                </section>
                <footer>
                    <CommentsTextarea onChange={this.handleOverallCommentsChange}
                                      placeholder="Overall Comments (Markdown-parsed)"
                                      value={this.props.overall_comments}
                                      valueHTML={this.props.overall_comments
                                          .replace(/&/g, "&amp;")
                                          .replace(/"/g, "&quot;")
                                          .replace(/</g, "&lt;")
                                          .replace(/>/g, "&gt;")
                                          .replace(/\n/g, "<br />")
                                          + '<p><small>TODO: Render markdown</small></p>'}
                                      minRows={3}
                    />
                </footer>
            </div>
        );
    }
});

function mapStateToProps(state) {
    return {
        submission_id: state.get("submission_id"),
        name: state.get("submission_name"),
        is_late: state.get("submission_is_late"),
        overall_comments: state.get("submission_overall_comments"),
        current_score: state.get("submission_current_score"),
        max_score: state.get("submission_max_score"),
        grades: state.get("submission_grades")
    };
}

export default ReactRedux.connect(mapStateToProps)(Submission);
