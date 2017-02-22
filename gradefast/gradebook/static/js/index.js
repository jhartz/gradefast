import * as React from "react";
import * as ReactDOM from "react-dom";
import * as ReactRedux from "react-redux";

import {reportError} from "./common";
import {actions} from "./actions";
import {store, initStore} from "./store";

import GradeBook from "./components/GradeBook";

const Container = React.createClass({
    render() {
        return (
            <GradeBook />
        );
    },

    closeEventSource() {
        if (this.state.eventSource) {
            this.state.eventSource.close();
            this.setState({eventSource: null});
        }
    },

    componentDidMount() {
        const eventSource = new EventSource(CONFIG.BASE + "events.stream");
        this.setState({eventSource});

        eventSource.addEventListener("update", (event) => {
            // Parse the JSON data
            let jsonData;
            try {
                jsonData = JSON.parse(event.data);
            } catch (err) {
                reportError(true, "event.stream", "update", event.data, event);
                return;
            }

            if (!jsonData) return;
            console.log("EVENT (update):", jsonData);

            if (jsonData.list) {
                // Update our list of submissions
                store.dispatch(actions.setList(jsonData.list));
            }
            /*
            if (jsonData.grade_structure) {
                // Update our grade structure with a new one
                store.dispatch(actions.setGradeStructure(jsonData.grade_structure));
            }
            */
            if (jsonData.submission_index) {
                // Tell the forces at large to go to this submission
                store.dispatch(actions.goToSubmission(jsonData.submission_index));
            }

            if (!jsonData.list && !jsonData.submission_index) {
                console.error("TODO: INVALID EVENT");
            }
        });

        eventSource.addEventListener("done", (event) => {
            // All done! Close the event source
            console.log("EVENT: Closing event source");
            this.closeEventSource();
        });
    },

    componentWillUnmount() {
        this.closeEventSource();
    }
});

window.addEventListener("load", (event) => {
    initStore();
    ReactDOM.render(
            <ReactRedux.Provider store={store}>
                <Container />
            </ReactRedux.Provider>,
        document.getElementById("root"));
}, false);
