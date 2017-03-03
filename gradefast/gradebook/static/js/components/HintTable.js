import * as React from "react";

import {actions} from "../actions";
import {store} from "../store";

import {id} from "../common";
import SizingTextarea from "./SizingTextarea";

const HintTable = React.createClass({
    getInitialState() {
        return {
            currentlyEditing: -1,
            oldValue: null,
            textareaValue: "",
            numberValue: "0"
        };
    },

    handleTextareaChange(value) {
        this.setState({
            textareaValue: value
        });
    },

    handleNumberChange(event) {
        this.setState({
            numberValue: event.target.value
        });
    },

    handleSetHintEnabled(index, isEnabled) {
        store.dispatch(actions.grade_setHint(this.props.path, index, isEnabled));
    },

    handleEditHint(event, index) {
        event.preventDefault();

        this.setState({
            currentlyEditing: index,
            oldValue: this.props.hints.get(index).get("value") || 0,
            textareaValue: this.props.hints.get(index).get("name") || ""
        });
    },

    handleSubmit(event) {
        event.preventDefault();

        const name = this.state.textareaValue.trim();
        const value = Number(this.state.numberValue.trim());

        if (!name) {
            alert("Please specify a name.");
            return;
        }
        if (isNaN(value)) {
            alert("Invalid value: \"" + this.state.numberValue.trim() + "\"");
            return;
        }

        if (this.state.currentlyEditing === -1) {
            store.dispatch(actions.grade_addHint(
                this.props.path,
                {name, value}
            ));
        } else {
            if (value !== this.state.oldValue) {
                if (!confirm(
                        "You changed the value for this hint from " + this.state.oldValue + " " +
                        "to " + value + ". This will affect ALL submissions that have this " +
                        "hint enabled, including ones that have already been graded. \n" +
                        "Are you sure you want to continue?"
                    )) {
                    return;
                }
            }

            store.dispatch(actions.grade_editHint(
                this.props.path,
                this.state.currentlyEditing,
                {name, value}
            ));
        }

        this.setState(this.getInitialState());
    },

    handleCancel(event) {
        event.preventDefault();

        this.setState(this.getInitialState());
    },

    render() {
        return (
            <form onSubmit={this.handleSubmit}>
            <table className="hint-table"><tbody>
                {this.props.hints.map((hint, index) => {
                    const isEnabled = this.props.hints_set.get("" + index);
                    if (this.state.currentlyEditing === index) return (
                        <tr key={"editing-" + index}>
                            <td style={{width: "1px", whiteSpace: "nowrap"}}>
                                <input type="checkbox"
                                       id={id(this.props.path, index, "enabled")}
                                       disabled="disabled"
                                       checked={isEnabled}
                                       onChange={(event) => this.handleSetHintEnabled(index, event.target.checked)}
                                />
                            </td>
                            <td style={{width: "1px", whiteSpace: "nowrap"}}>
                                <input type="number"
                                       className="flat"
                                       size="5"
                                       value={this.state.numberValue}
                                       onChange={this.handleNumberChange}
                                />
                            </td>
                            <td>
                                <SizingTextarea onChange={this.handleTextareaChange}
                                                value={this.state.textareaValue}
                                                className="flat"
                                                style={{width: "100%"}}
                                />
                            </td>
                            <td style={{width: "1px", whiteSpace: "nowrap"}}>
                                <input type="submit"
                                       className="flat"
                                       value="Save"
                                />
                                <button className="flat"
                                        type="button"
                                        onClick={this.handleCancel}>Cancel</button>
                            </td>
                        </tr>
                    );
                    else return (
                        <tr key={"" + index}>
                            <td style={{width: "1px", whiteSpace: "nowrap"}}>
                                <input type="checkbox"
                                       id={id(this.props.path, index, "enabled")}
                                       checked={isEnabled}
                                       onChange={(event) => this.handleSetHintEnabled(index, event.target.checked)}
                                />
                            </td>
                            <td style={{textAlign: "right", whiteSpace: "nowrap"}}>
                                <label htmlFor={id(this.props.path, index, "enabled")}>
                                    <b>{hint.get("value") ? (hint.get("value") + ":") : undefined}&nbsp;</b>
                                </label>
                            </td>
                            <td>
                                <label htmlFor={id(this.props.path, index, "enabled")}>
                                    <i>{hint.get("name")}</i>
                                </label>
                            </td>
                            <td style={{width: "1px", whiteSpace: "nowrap"}}>
                                <button className="flat"
                                        type="button"
                                        onClick={(event) => this.handleEditHint(event, index)}>
                                    Edit
                                </button>
                            </td>
                        </tr>
                    );
                })}

                {this.state.currentlyEditing !== -1 ? undefined :
                    <tr>
                        <td style={{width: "1px", whiteSpace: "nowrap"}}>
                            <input type="checkbox" disabled="disabled" />
                        </td>
                        <td style={{width: "1px", whiteSpace: "nowrap"}}>
                            {!this.state.textareaValue ? <span>&nbsp;</span> :
                                <input type="number"
                                       className="flat"
                                       size="5"
                                       value={this.state.numberValue}
                                       onChange={this.handleNumberChange}
                                />
                            }
                        </td>
                        <td>
                            <SizingTextarea onChange={this.handleTextareaChange}
                                            value={this.state.textareaValue}
                                            className="flat"
                                            style={{width: "100%"}}
                            />
                        </td>
                        <td style={{width: "1px", whiteSpace: "nowrap"}}>
                            <input type="submit" className="flat" value="Add" />
                        </td>
                    </tr>
                }
            </tbody></table>
            </form>
        );
    }
});

export default HintTable;
