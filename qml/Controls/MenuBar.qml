import QtQuick
import QtQuick.Controls.Basic
import Modules

MenuBar {
    delegate: MenuBarItem {
        id: delegateMenuBarItem
        states: [
            State {
                name: "disabled"
                when: !delegateMenuBarItem.enabled
                PropertyChanges { target: delegateMenuBarItemText; opacity: 0.3 }
                PropertyChanges { target: delegateMenuBarItemBackground; opacity: 0.3 }
            },
            State {
                name: "highlight"
                when: delegateMenuBarItem.highlighted
                PropertyChanges { target: delegateMenuBarItemText; font.bold: true; color: Colors.selectionText }
                PropertyChanges { target: delegateMenuBarItemBackground; color: Colors.selectionBackground }
            }
        ]
        contentItem: Text {
            id: delegateMenuBarItemText
            text: Helper.stylizeMnemonics(delegateMenuBarItem.text)
            anchors.centerIn: parent
            font.pixelSize: Helper.fontPixelSize
            elide: Text.ElideRight
            color: Colors.textPrimary
        }
        background: Rectangle {
            id: delegateMenuBarItemBackground
            color: "transparent"
        }
    }
    background: Rectangle {
        color: Colors.panelBackground
        Rectangle {
            color: Colors.borderColor
            width: parent.width
            height: 1
            anchors.bottom: parent.bottom
        }
    }
}
