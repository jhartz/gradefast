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
        let className = "row-grade";
        if (this.props.grade.get("touched")) {
            className += " row-grade-touched";
        }
        return (
            <div className={className}>
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
                                           path={this.props.path}
                                />
                            </div>
                        }
                    </td>
                    <td>
                        {!this.props.grade.get("enabled") ? undefined :
                            <em dangerouslySetInnerHTML={{__html: this.props.grade.get("notes_html")}}/>
                        }
                        {!this.props.grade.get("enabled") ? undefined :
                            <CommentsTextarea onChange={this.handleCommentsChange}
                                              placeholder={"Comments " + CONFIG.MARKDOWN_MSG}
                                              value={this.props.grade.get("comments")}
                                              valueHTML={this.props.grade.get("comments_html")}
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
