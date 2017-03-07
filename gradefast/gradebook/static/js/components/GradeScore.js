import * as React from "react";

import {actions} from "../actions";
import {id} from "../utils";
import {store} from "../store";

import CommentsTextarea from "./utils/CommentsTextarea";
import HintTable from "./utils/HintTable";

import GradeTitle from "./GradeTitle";

const GradeScore = React.createClass({
    handleSetEnabled(isEnabled) {
        store.dispatch(actions.grade_setEnabled(this.props.path, isEnabled));
    },

    handleScoreChange(event) {
        const value = Number(event.target.value);
        if (isNaN(value)) {
            console.error("Invalid value: \"" + event.target.value + "\"");
            return;
        }
        store.dispatch(actions.grade_setScore(this.props.path, value));
    },

    handleCommentsChange(value) {
        store.dispatch(actions.grade_setComments(this.props.path, value));
    },

    render() {
        return (
            <div className="row-grade">
                <table className="row-grade-table"><tbody><tr>
                    <td>
                        <GradeTitle path={this.props.path}
                                    grade={this.props.grade}
                                    onSetEnabled={this.handleSetEnabled}
                        />
                        {!this.props.grade.get("enabled") ? undefined :
                            <div className="row-grade-body">
                                <p>
                                    <input type="number"
                                           id={id(this.props.path, "score")}
                                           size="5"
                                           value={this.props.grade.get("score")}
                                           onChange={this.handleScoreChange}
                                    />
                                    {!this.props.grade.get("points") ? undefined :
                                        <label htmlFor={id(this.props.path, "score")}
                                               className="noselect"
                                               style={{fontWeight: "bold"}}>
                                            &nbsp;&nbsp;/ {this.props.grade.get("points")}
                                        </label>
                                    }
                                </p>
                                <HintTable hints={this.props.grade.get("hints")}
                                           hints_set={this.props.grade.get("hints_set")}
                                           path={this.props.path}
                                />
                            </div>
                        }
                    </td>
                    <td>
                        {!this.props.grade.get("enabled") ? undefined :
                            (this.props.grade.get("note") || "")
                                .split("\n")
                                .map((note, index) => <em key={index}>{note}<br /></em>)}
                        {!this.props.grade.get("enabled") ? undefined :
                            <CommentsTextarea onChange={this.handleCommentsChange}
                                              placeholder="Comments (Markdown-parsed)"
                                              value={this.props.grade.get("comments")}
                                              valueHTML={this.props.grade.get("comments")
                                                  .replace(/&/g, "&amp;")
                                                  .replace(/"/g, "&quot;")
                                                  .replace(/</g, "&lt;")
                                                  .replace(/>/g, "&gt;")
                                                  .replace(/\n/g, "<br />")
                                              + '<br /><small>TODO: Render markdown</small>'}
                                              minRows={2}
                                              fillParent={true}
                            />
                        }
                    </td>
                </tr></tbody></table>
            </div>
        );
    }
});

export default GradeScore;
