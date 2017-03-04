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

    /**
     * Resize the textarea so that it is:
     *   - Smaller than its max height (either specified via the "maxHeightPx",
     *     as a number or a function returning a number)
     *   - Given that limit, as large as possible so that it:
     *       - Contains at least "minRows" rows, and
     *       - Fits its contents, and
     *       - Fills its parent (if the "fillParent" prop is true)
     */
    resize() {
        const textarea = this.elem;
        const parent = textarea.parentNode;

        // The default "max height" (which is also the maximum "max height") is the height of the
        // viewport, minus some room for the header, the footer, a bit of padding, etc.
        let maxHeightPx = document.documentElement.clientHeight;
        if (maxHeightPx > 200) {
            maxHeightPx -= 75;
        }

        if (typeof this.props.maxHeightPx == "function") {
            maxHeightPx = Math.min(maxHeightPx, this.props.maxHeightPx());
        } else if (this.props.maxHeightPx) {
            maxHeightPx = Math.min(maxHeightPx, this.props.maxHeightPx);
        }

        // Reset the height
        textarea.style.height = "auto";

        // Collect some stats
        const origHeight = textarea.scrollHeight + 3;
        const origParentHeight = parent.scrollHeight;

        // Calculate the new height
        let currentHeight = origHeight;
        if (currentHeight >= maxHeightPx) {
            currentHeight = maxHeightPx;
        } else if (this.props.fillParent) {
            if (origHeight < origParentHeight) {
                // Increase this guy's height until its parent
                // feels the bulge, or until we hit the max
                while (parent.scrollHeight <= origParentHeight &&
                        currentHeight < maxHeightPx) {
                    currentHeight += 2;
                    textarea.style.height = currentHeight + "px";
                }
                currentHeight -= 2;
            }
        }

        // Set the new height
        textarea.style.height = currentHeight + "px";
    },

    render() {
        let initialStyle = this.props.style || {};
        initialStyle.height = "100%";

        // It's important that this isn't wrapped with any other element
        // so "fillParent" still works
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
        if (this.props.focusOnMount) {
            this.elem.focus();
        }

        window.addEventListener("resize", this.resize, false);
    },

    componentWillUnmount() {
        window.removeEventListener("resize", this.resize, false);
    }
});

export default SizingTextarea;
