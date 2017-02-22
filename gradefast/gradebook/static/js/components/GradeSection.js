import * as React from "react";

import {actions} from "../actions";
import {store} from "../store";

import GradeHeader from "./GradeHeader";
import GradeList from "./GradeList";

const GradeSection = React.createClass({
    handleSetEnabled(event) {
        store.dispatch(actions.grade_setEnabled(this.props.path, event.target.checked));
    },

    render() {
        return (
            <div>
                <GradeHeader path={this.props.path}
                             grade={this.props.grade}
                             setEnabledHandler={this.handleSetEnabled}
                />
                <p>GradeSection: path is {JSON.stringify(this.props.path)}</p>
                <p>TODO: Section deductions</p>
                <div className="row-children">
                    <GradeList path={this.props.path} grades={this.props.grade.get("children")} />
                </div>
            </div>
        );
    }
});

export default GradeSection;
