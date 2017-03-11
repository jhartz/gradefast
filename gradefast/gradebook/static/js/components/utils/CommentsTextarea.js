import * as React from "react";

import SizingTextarea from "./SizingTextarea";

const CommentsTextarea = React.createClass({
    getInitialState() {
        return {
            focused: false
        };
    },

    handleChange(value) {
        this.props.onChange(value);
    },

    handleUnfocus() {
        this.setState({
            focused: false
        });
    },

    handleFocus() {
        this.setState({
            focused: true
        });
    },

    render() {
        if (this.state.focused) {
            // It's important that this isn't wrapped with any other element
            // so "fillParent" still works
            return (
                <SizingTextarea onChange={this.handleChange}
                                onFocus={this.handleFocus}
                                onBlur={this.handleUnfocus}
                                // The rest of these are just passed through
                                // from us to the SizingTextarea
                                className={this.props.className}
                                style={this.props.style}
                                placeholder={this.props.placeholder}
                                value={this.props.value}
                                minRows={this.props.minRows}
                                maxHeightPx={this.props.maxHeightPx}
                                fillParent={this.props.fillParent}
                                focusOnMount={true}
                />
            );
        } else {
            let style = {};
            if (typeof this.props.maxHeightPx == "function") {
                style.maxHeight = this.props.maxHeightPx() + "px";
            } else if (this.props.maxHeightPx) {
                style.maxHeight = this.props.maxHeightPx + "px";
            }
            if (this.props.minRows) {
                style.minHeight = (this.props.minRows + 1) + "em";
            }

            return (
                <div className="inset"
                     style={style}
                     onClick={this.handleFocus}>
                    {this.props.value
                        ? <div dangerouslySetInnerHTML={{__html: this.props.valueHTML}}/>
                        : <em style={{opacity: 0.7}}>{this.props.placeholder}</em>
                    }
                </div>
            );
        }
    }
});

export default CommentsTextarea;
