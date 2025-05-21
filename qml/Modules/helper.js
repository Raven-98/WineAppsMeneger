.pragma library

const fontPixelSize = 14
const iconSmallSize = 16

function stylizeMnemonics(text) {
    let replaceFunction = (match, p1, p2, p3) => {
        if (p2 === "&") {
            return p1.concat(p2, p3)
        }
        return p1.concat("<u>", p2, "</u>", p3)
    }
    return text.replace(/([^&]*)&(.)([^&]*)/g, replaceFunction)
}

function textWidth(text, fontMetrics) {
    let ret = 0
    text.split("\n").forEach(element => {
        ret = Math.max(ret,
            fontMetrics.advanceWidth(text))
    })
    return Math.ceil(ret)
}

function widthMenuBar(contentModel, fontMetrics, cWidth) {
    let w = 0
    for (var i = 0; i < contentModel.count; i++) {
        let item = contentModel.get(i)
        if (item.objectName !== "menuSeparator") {
            let tw = item.leftPadding + item.rightPadding
            if (item.icon.source != "")
                tw += (cWidth - 2) + item.spacing
            tw += textWidth(item.text, fontMetrics) + item.spacing
            if (item.action && item.action.shortcut)
                tw += textWidth(item.action.shortcut, fontMetrics) + item.spacing
            if (item.subMenu)
                tw += (cWidth - 2) + item.spacing
            if (item.checkable)
                tw += (cWidth - 2) + item.spacing
            w = Math.max(w, tw)
        }
    }
    return w
}

function buttWidth(buttText, fontMetrics, cWidth) {
    return Math.max(cWidth, Math.ceil(textWidth(buttText.text, fontMetrics)) + 6)
}
