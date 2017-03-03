import * as React from "react";

const SizingTextarea = React.createClass({
    handleChange(event) {
        this.props.onChange(event.target.value);
        this.resize();
    },

    handleFocus(event) {
        this.props.onFocus && this.props.onFocus();
    },

    handleBlur(event) {
        this.props.onBlur && this.props.onBlur();
    },

    resize() {
        const maxHeightPx = this.props.maxHeightPx || 140;

        // Reset the height
        this.elem.style.height = "auto";
        // Calculate new height
        const newHeight = Math.min(this.elem.scrollHeight + 3, maxHeightPx);
        this.elem.style.height = newHeight + "px";
        //this.elem.parentNode.style.height = (newHeight + 27) + "px";
    },

    render() {
        let initialStyle = this.props.style || {};
        initialStyle.height = "100%";

        return <textarea ref={(elem) => this.elem = elem}
                         className={this.props.className || ""}
                         style={initialStyle}
                         placeholder={this.props.placeholder || ""}
                         value={this.props.value}
                         onChange={this.handleChange}
                         onFocus={this.handleFocus}
                         onBlur={this.handleBlur}
                         rows={this.props.minRows || 1}
        />
    },

    componentDidMount() {
        this.resize();
    }
});

export default SizingTextarea;
