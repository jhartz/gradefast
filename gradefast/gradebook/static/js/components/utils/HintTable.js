import * as React from "react";

import {actions} from "../../actions";
import {id} from "../../utils";
import {store} from "../../store";

import SizingTextarea from "./SizingTextarea";

const HintTable = React.createClass({
    getInitialState() {
        return {
            currentlyEditing: -1,
            oldValue: null,
            forceShowTextarea: false,
            textareaValue: "",
            numberValue: "0"
        };
    },

    handleAddHintClick(event) {
        event.preventDefault();

        this.setState({
            forceShowTextarea: true
        });
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
            forceShowTextarea: false,
            textareaValue: this.props.hints.get(index).get("name") || "",
            numberValue: "" + (this.props.hints.get(index).get("value") || 0)
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
                            <td style={{width: "1px"}}>
                                <input type="checkbox"
                                       id={id(this.props.path, index, "enabled")}
                                       disabled="disabled"
                                       checked={isEnabled}
                                       onChange={(event) => this.handleSetHintEnabled(index, event.target.checked)}
                                />
                            </td>
                            <td style={{width: "1px"}}>
                                <input type="number"
                                       size="5"
                                       value={this.state.numberValue}
                                       onChange={this.handleNumberChange}
                                />
                            </td>
                            <td>
                                <SizingTextarea onChange={this.handleTextareaChange}
                                                placeholder="Hint Name (Markdown-parsed)"
                                                value={this.state.textareaValue}
                                                style={{width: "100%"}}
                                />
                            </td>
                            <td style={{width: "1px"}}>
                                <input type="submit"
                                       value="Save"
                                />
                                <button type="button"
                                        onClick={this.handleCancel}>Cancel</button>
                            </td>
                        </tr>
                    );
                    else return (
                        <tr key={"" + index}>
                            <td style={{width: "1px"}}>
                                <input type="checkbox"
                                       id={id(this.props.path, index, "enabled")}
                                       checked={isEnabled}
                                       onChange={(event) => this.handleSetHintEnabled(index, event.target.checked)}
                                />
                            </td>
                            <td style={{textAlign: "right", whiteSpace: "nowrap"}}>
                                <label htmlFor={id(this.props.path, index, "enabled")}>
                                    <strong>{hint.get("value") ? (hint.get("value") + ":") : undefined}&nbsp;</strong>
                                </label>
                            </td>
                            <td>
                                <label htmlFor={id(this.props.path, index, "enabled")}>
                                    {hint.get("name_html")
                                        ? <span dangerouslySetInnerHTML={{__html: hint.get("name_html")}}/>
                                        : hint.get("name")
                                    }
                                </label>
                            </td>
                            <td style={{width: "1px"}}>
                                <button type="button"
                                        onClick={(event) => this.handleEditHint(event, index)}>
                                    Edit
                                </button>
                            </td>
                        </tr>
                    );
                })}

                {this.state.currentlyEditing !== -1 ? undefined :
                    <tr>
                        <td style={{width: "1px"}}>
                            <input type="checkbox" disabled="disabled" />
                        </td>
                        <td style={{width: "1px"}}>
                            {!this.state.textareaValue ? <span>&nbsp;</span> :
                                <input type="number"
                                       size="5"
                                       value={this.state.numberValue}
                                       onChange={this.handleNumberChange}
                                />
                            }
                        </td>
                        <td>
                            {(this.state.textareaValue || this.state.forceShowTextarea)
                                ? <SizingTextarea onChange={this.handleTextareaChange}
                                                  placeholder="Add a new hint (Markdown-parsed)"
                                                  value={this.state.textareaValue}
                                                  style={{width: "100%"}}
                                                  focusOnMount={this.state.forceShowTextarea}
                                  />
                                : <a href="#poundsign" onClick={this.handleAddHintClick}>
                                      Add a new hint
                                  </a>
                            }
                        </td>
                        <td style={{width: "1px"}}>
                            {(this.state.textareaValue || this.state.forceShowTextarea)
                                ? <span>
                                      <input type="submit" value="Add"/>
                                      <button type="button"
                                              onClick={this.handleCancel}>Cancel</button>
                                  </span>
                                : <span>
                                      {/* This is here just for spacing, so the layout doesn't jump
                                          when we show the Add/Cancel or the Save/Cancel buttons */}
                                      <button type="button"
                                              disabled="disabled"
                                              style={{visibility: "hidden"}}>
                                          Cancel
                                      </button>
                                  </span>
                            }
                        </td>
                    </tr>
                }
            </tbody></table>
            </form>
        );
    }
});

export default HintTable;
