import * as React from "react";

import {actions} from "../actions";
import {store} from "../store";

import GradeHeader from "./GradeHeader";

const GradeItem = React.createClass({
    handleSetEnabled(isEnabled) {
        store.dispatch(actions.grade_setEnabled(this.props.path, isEnabled));
    },

    render() {
        return (
            <div>
                <GradeHeader path={this.props.path}
                             grade={this.props.grade}
                             hintsTitle="Hints"
                             onSetEnabled={this.handleSetEnabled}
                />
                {!this.props.grade.get("enabled") ? undefined :
                    <div>
                        <p><code>{JSON.stringify(this.props.grade, null, 2)}</code></p>
                    </div>
                }
            </div>
        );
    }
});

export default GradeItem;
