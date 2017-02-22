import * as React from "react";

import {actions} from "../actions";
import {store} from "../store";

import GradeHeader from "./GradeHeader";

const GradeItem = React.createClass({
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
                <p>GradeItem: path is {JSON.stringify(this.props.path)}</p>
                <pre>{JSON.stringify(this.props.grade)}</pre>
            </div>
        );
    }
});

export default GradeItem;
