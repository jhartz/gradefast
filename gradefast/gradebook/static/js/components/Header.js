import * as React from "react";
import * as ReactRedux from "react-redux";

import {actions} from "../actions";
import {store} from "../store";

const Header = React.createClass({
    lateChangeHandler(event) {
        store.dispatch(actions.setLate(event.target.checked));
    },

    titleClickHandler(event) {
        event.preventDefault();
        store.dispatch(actions.toggleListVisibility());
    },

    render() {
        let score;
        if (this.props.showScore) {
            score = (
                <span>
                    <label>Current Score: </label>{this.props.current_score}&nbsp;/&nbsp;{this.props.max_score}
                        &emsp;
                        <input id="late"
                               type="checkbox"
                               value={this.props.is_late}
                               onChange={this.lateChangeHandler}
                        /><label htmlFor="late"> Late?</label>
                        &emsp;
                </span>
            );
        }

        return (
            <header>
                <h2>
                    <span>
                        {score}
                        <a href={`${CONFIG.BASE}grades.csv`}
                           title="Download Grades as CSV"
                           target="_blank">
                            <img src={`${CONFIG.STYLE_BASE}csv.png`}/>
                        </a>
                        <a href={`${CONFIG.BASE}grades.json`}
                           title="Download Grades as JSON"
                           target="_blank">
                            <img src={`${CONFIG.STYLE_BASE}json.png`}/>
                        </a>
                    </span>
                </h2>
                <h1>
                    <a href="#" className="no-underline" onClick={this.titleClickHandler}>
                        {this.props.list_visible ? <small>&#x25B2;</small> : <small>&#x25BC;</small>}
                        &nbsp;&nbsp;
                        {this.props.children}
                    </a>
                </h1>
            </header>
        );
    }
});

function mapStateToProps(state) {
    return {
        list_visible: state.get("list_visible"),

        current_score: state.get("submission_current_score"),
        max_score: state.get("submission_max_score"),
        is_late: state.get("submission_is_late")
    }
}

export default ReactRedux.connect(mapStateToProps)(Header);
