import * as React from "react";

import {actions} from "../actions";
import {store} from "../store";

import HintTable from "./utils/HintTable";

import GradeList from "./GradeList";
import GradeTitle from "./GradeTitle";

const GradeSection = React.createClass({
    handleSetEnabled(isEnabled) {
        store.dispatch(actions.grade_setEnabled(this.props.path, isEnabled));
    },

    render() {
        return (
            <div className="row-grade">
                <table className="row-grade-table"><tbody><tr>
                    <td style={{minWidth: "50%"}}>
                        <GradeTitle path={this.props.path}
                                    grade={this.props.grade}
                                    hintsTitle="Section Hints"
                                    onSetEnabled={this.handleSetEnabled}
                        />
                        {!this.props.grade.get("enabled") ? undefined :
                            <div className="row-grade-body">
                                <HintTable hints={this.props.grade.get("hints")}
                                           hints_set={this.props.grade.get("hints_set")}
                                           path={this.props.path}
                                />
                            </div>
                        }
                    </td>
                    <td>
                        {!this.props.grade.get("enabled") ? undefined :
                            <em dangerouslySetInnerHTML={{__html: this.props.grade.get("note_html")}}/>
                        }
                    </td>
                </tr></tbody></table>
                {!this.props.grade.get("enabled") ? undefined :
                    <div className="row-children">
                        <GradeList path={this.props.path} grades={this.props.grade.get("children")}/>
                    </div>
                }
            </div>
        );
    }
});

export default GradeSection;
