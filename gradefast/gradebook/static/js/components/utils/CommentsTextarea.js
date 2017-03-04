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
        if (this.state.focused || !this.props.value) {
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
                                focusOnMount={this.state.focused}
                />
            );
        } else {
            let style = {};
            if (typeof this.props.maxHeightPx == "function") {
                style.maxHeight = this.props.maxHeightPx() + "px";
            } else if (this.props.maxHeightPx) {
                style.maxHeight = this.props.maxHeightPx + "px";
            }
            return (
                <div className="inset"
                     style={style}
                     onClick={this.handleFocus}
                     dangerouslySetInnerHTML={{__html: this.props.valueHTML}}
                />
            );
        }
    }
});

export default CommentsTextarea;
