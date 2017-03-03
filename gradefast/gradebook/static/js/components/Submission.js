import * as Immutable from "immutable";
import * as React from "react";
import * as ReactRedux from "react-redux";

import {actions} from "../actions";
import {store} from "../store";

import SizingTextarea from "./SizingTextarea";
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
                                   currentScore={this.props.currentScore}
                                   maxScore={this.props.maxScore}
                                   isLate={this.props.isLate}
                                   setLateHandler={this.setLate} />
                    <h1><a href="#" onClick={(event) => {
                        event.preventDefault();
                        this.props.showListHandler();
                    }}>{this.props.index}: {this.props.name || "GradeFast"}</a></h1>
                </header>
                <section>
                    <GradeList path={Immutable.List()} grades={this.props.grades} />
                </section>
                <footer>
                    <SizingTextarea onChange={this.handleOverallCommentsChange}
                                    placeholder="Overall Comments (Markdown-parsed)"
                                    value={this.props.overallComments}
                                    minRows={3}
                    />
                </footer>
            </div>
        );
    }
});

function mapStateToProps(state) {
    return {
        index: state.get("submission_index"),
        name: state.get("submission_name"),
        isLate: state.get("submission_is_late"),
        overallComments: state.get("submission_overall_comments"),
        currentScore: state.get("submission_current_score"),
        maxScore: state.get("submission_max_score"),
        grades: state.get("submission_grades")
    };
}

export default ReactRedux.connect(mapStateToProps)(Submission);
