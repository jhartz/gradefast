import * as React from "react";

import {actions} from "../actions";
import {store} from "../store";

import GradeHeader from "./GradeHeader";
import GradeList from "./GradeList";

const GradeSection = React.createClass({
    handleSetEnabled(isEnabled) {
        store.dispatch(actions.grade_setEnabled(this.props.path, isEnabled));
    },

    render() {
        return (
            <div>
                <GradeHeader path={this.props.path}
                             grade={this.props.grade}
                             hintsTitle="Section Hints"
                             onSetEnabled={this.handleSetEnabled}
                />
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
