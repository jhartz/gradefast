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
                    <label>Current Score: </label>{this.props.points_earned}&nbsp;/&nbsp;{this.props.points_possible}
                        &emsp;
                        <input id="late"
                               type="checkbox"
                               checked={this.props.is_late}
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
                        {this.props.data_key === null ? undefined :
                            <span>
                                <a href={`${CONFIG.BASE}grades.csv?data_key=${encodeURIComponent(this.props.data_key)}`}
                                   title="Download Grades as CSV"
                                   target="_blank">
                                    <img src={`${CONFIG.STYLE_BASE}csv.png`}/>
                                </a>
                                <a href={`${CONFIG.BASE}grades.json?data_key=${encodeURIComponent(this.props.data_key)}`}
                                   title="Download Grades as JSON"
                                   target="_blank">
                                    <img src={`${CONFIG.STYLE_BASE}json.png`}/>
                                </a>
                            </span>
                        }
                    </span>
                </h2>
                <h1>
                    <a href="#poundsign" className="no-underline" onClick={this.titleClickHandler}>
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
        data_key: state.get("data_key"),
        list_visible: state.get("list_visible"),

        points_earned: state.get("submission_points_earned"),
        points_possible: state.get("submission_points_possible"),
        is_late: state.get("submission_is_late")
    }
}

export default ReactRedux.connect(mapStateToProps)(Header);
