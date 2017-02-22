import * as React from "react";

import {id} from "../common";

export default ({path, grade, setEnabledHandler}) => (
    <div>
        <hr className="row-divider" />
        {
            (grade.get("note") || undefined) && (
                <div className="row-notes">
                    {grade.get("note").split("\n").map((note) => <em key={note}>{note}<br /></em>)}
                </div>
            )
        }
        <div className="row-title">
            {
                (function () {
                    const titleElem = (
                        <label htmlFor={id(path, "enabled")}>
                            <input id={id(path, "enabled")}
                                   type="checkbox"
                                   className="big-checkbox"
                                   onClick={setEnabledHandler} />
                            {grade.get("name")}
                        </label>
                    );
                    switch (path.size) {
                    case 1:
                        return (<h3>{titleElem}</h3>);
                    case 2:
                        return (<h4>{titleElem}</h4>);
                    case 3:
                        return (<h5>{titleElem}</h5>);
                    default:
                        return (<h6>{titleElem}</h6>);
                    }
                })()
            }
        </div>
    </div>
);
