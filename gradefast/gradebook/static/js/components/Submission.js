import * as Immutable from "immutable";
import * as React from "react";
import * as ReactRedux from "react-redux";

import {actions} from "../actions";
import {SONGS} from "../SONGS";
import {store} from "../store";

import CommentsTextarea from "./utils/CommentsTextarea";

import Header from "./Header";
import GradeList from "./GradeList";

const Submission = React.createClass({
    handleOverallCommentsChange(value) {
        store.dispatch(actions.setOverallComments(value));
    },

    setLate(isLate) {
        store.dispatch(actions.setLate(isLate));
    },

    render() {
        const song = SONGS[Math.floor(Math.random() * SONGS.length)];

        return (
            <div className="container">
                <Header showScore={true}
                        currentScore={this.props.current_score}
                        maxScore={this.props.max_score}
                        isLate={this.props.is_late}
                        onSetLate={this.setLate}>
                    <h1><a href="#" onClick={(event) => {
                        event.preventDefault();
                        this.props.showListHandler();
                    }}>{this.props.submission_id}: {this.props.name || "GradeFast"}</a></h1>
                </Header>
                <section>
                    <div style={{textAlign: "right"}}>
                        <a href={song.link} target="_blank">{song.snippet}</a>
                    </div>
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
                                          + '<br /><small>TODO: Render markdown</small>'}
                                      minRows={3}
                                      maxHeightPx={() => Math.round(document.documentElement.clientHeight * 0.25)}
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
