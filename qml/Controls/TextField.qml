import QtQuick
import QtQuick.Controls.Basic

import Modules

TextField {
    id: root
    implicitWidth: 100
    implicitHeight: 32
    background: Rectangle {
        color: Colors.textfaildColor
        border.width: 2
        border.color: root.activeFocus ? Colors.accent : Colors.borderColor
    }
    color: Colors.textInverted
    font.pixelSize: Helper.fontPixelSize
    selectByMouse: true
    selectionColor: Colors.selectionBackground
    opacity: enabled ? 1.0 : 0.3

    onEditingFinished: text = text.replace(/(\r\n|\n|\r)/gm," ")
}
