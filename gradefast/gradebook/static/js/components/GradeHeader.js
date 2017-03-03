import * as React from "react";

import {id} from "../common";
import HintTable from "./HintTable";

export default ({path, grade, hintsTitle, onSetEnabled}) => (
    <div>
        <hr />
        <table className="header-table"><tbody><tr>
            <td>
                {
                    (function () {
                        const titleElem = (
                            <label htmlFor={id(path, "enabled")}>
                                <input id={id(path, "enabled")}
                                       type="checkbox"
                                       className="big-checkbox"
                                       checked={grade.get("enabled")}
                                       onChange={(event) => onSetEnabled(event.target.checked)} />
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
                    })()
                }

                {!grade.get("enabled") ? undefined :
                    <div>
                        <div className="subtitle">{hintsTitle}</div>
                        <HintTable hints={grade.get("hints")}
                                   hints_set={grade.get("hints_set")}
                                   path={path}
                        />
                    </div>
                }
            </td>
            {!grade.get("note") ? undefined :
                <td>{grade.get("note").split("\n").map((note) => <em key={note}>{note}<br /></em>)}</td>
            }
        </tr></tbody></table>
    </div>
);
