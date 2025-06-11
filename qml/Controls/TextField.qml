import QtQuick
import QtQuick.Controls.Basic

import Controls
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

    Menu {
        id: contextMenu
        light: true

        MenuItem {
            light: true
            text: qsTr("Cut")
            icon.source: highlighted ? "qrc:/img/cut-32.png" : "qrc:/img/cut-32-light.png"
            onTriggered: root.cut()
        }
        MenuItem {
            light: true
            text: qsTr("Copy")
            icon.source: highlighted ? "qrc:/img/copy-32.png" : "qrc:/img/copy-32-light.png"
            onTriggered: root.copy()
        }
        MenuItem {
            light: true
            text: qsTr("Paste")
            icon.source: highlighted ? "qrc:/img/paste-32.png" : "qrc:/img/paste-32-light.png"
            onTriggered: root.paste()
        }
        MenuSeparator { light: true }
        MenuItem {
            light: true
            text: qsTr("Select all")
            onTriggered: root.selectAll()
        }
    }

    MouseArea {
        anchors.fill: parent
        acceptedButtons: Qt.RightButton
        onClicked: (mouse)=> {
            if (mouse.button === Qt.RightButton) {
                contextMenu.x = mouse.x
                contextMenu.y = mouse.y
                contextMenu.open()
            }
        }
    }
}
