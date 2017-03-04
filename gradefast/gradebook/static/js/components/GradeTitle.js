import * as React from "react";

import {id} from "../common";

export default ({path, grade, onSetEnabled}) => {
    const titleElem = (
        <label htmlFor={id(path, "enabled")}>
            <input id={id(path, "enabled")}
                   type="checkbox"
                   className="big-checkbox"
                   checked={grade.get("enabled")}
                   onChange={(event) => onSetEnabled(event.target.checked)}/>
            {grade.get("name")}
        </label>
    );
    switch (path.size) {
        case 1:
            return <h3>{titleElem}</h3>;
        case 2:
            return <h4>{titleElem}</h4>;
        case 3:
            return <h5>{titleElem}</h5>;
        default:
            return <h6>{titleElem}</h6>;
    }
};
