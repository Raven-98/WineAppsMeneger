import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

import Modules

Menu {
    id:root

    readonly property int implWidth: 250
    readonly property int implHeight: 30
    property bool hovered: false
    readonly property bool isCustomMenu: true
    property bool light: false

    function changeWidth() {
        width = Helper.widthMenuBar(contentModel, fontMetrics, implHeight)
    }

    Component.onCompleted: changeWidth()

    delegate: MenuItem {
        id: menuItem

        onTextChanged: root.changeWidth()
        onHighlightedChanged: {
            if (menuItem.subMenu)
                degArrow.requestPaint()
            root.hovered = highlighted
        }

        opacity: enabled ? 1.0 : 0.3
        contentItem: RowLayout {
            spacing: menuItem.spacing
            Image {
                source: menuItem.icon.source
                height: (menuItem.icon.source != "" ? Helper.iconSmallSize : 0)
                width: (menuItem.icon.source != "" ? Helper.iconSmallSize : 0)
                Layout.preferredWidth: width
                Layout.preferredHeight: height
            }
            Text {
                text: menuItem.text
                font.pixelSize: Helper.fontPixelSize
                font.bold: menuItem.highlighted
                color: menuItem.highlighted ? Colors.selectionText : light ? "#000" : Colors.textPrimary
                Layout.fillWidth: true
            }
            Text {
                text: menuItem.action && menuItem.action.shortcut && menuItem.action.shortcut !== "" ? menuItem.action.shortcut.toString() : ""
                font.pixelSize: Helper.fontPixelSize
                color: light ? "#000" : Colors.textSecondary
            }
        }
        indicator: Item {
            x: !menuItem.mirrored ? menuItem.width - width
                                    - menuItem.rightPadding : menuItem.leftPadding
            y: menuItem.topPadding + (menuItem.availableHeight - height) / 2
            width: root.implHeight - 2
            height: root.implHeight - 2
            Rectangle {
                width: 18
                height: 18
                anchors.centerIn: parent
                visible: menuItem.checkable
                color: menuItem.highlighted ? Colors.selectionText : light ? "#000" : Colors.textPrimary
                radius: 3
            }
            Rectangle {
                width: 16
                height: 16
                anchors.centerIn: parent
                visible: menuItem.checkable
                color: "transparent"
                border.color: Colors.borderColor
                radius: 3
                Rectangle {
                    width: 8
                    height: 8
                    anchors.centerIn: parent
                    visible: menuItem.checked
                    color: Colors.panelAltBackground
                    radius: 2
                }
            }
        }
        arrow: Canvas {
            id: degArrow
            x: menuItem.mirrored ? menuItem.leftPadding : menuItem.width - width
                                   - menuItem.rightPadding
            y: menuItem.topPadding + (menuItem.availableHeight - height) / 2
            width: root.implHeight - 2
            height: root.implHeight - 2
            visible: menuItem.subMenu
            onPaint: {
                var ctx = getContext("2d")
                let wh = Math.round(root.implHeight * 1 / 3)
                ctx.fillStyle = menuItem.highlighted ? Colors.selectionText : light ? Colors.panelAltBackground : Colors.textPrimary
                ctx.moveTo(wh, wh)
                ctx.lineTo(width - wh, height / 2)
                ctx.lineTo(wh, height - wh)
                ctx.closePath()
                ctx.fill()
            }
        }
        background: Rectangle {
            anchors.fill: parent
            width: menuItem.width
            height: menuItem.height
            opacity: enabled ? 1 : 0.3
            color: menuItem.highlighted ? Colors.buttonHover : "transparent"
        }
    }
    background: Rectangle {
        implicitWidth: root.implWidth
        implicitHeight: root.implHeight
        color: !light ? Colors.panelAltBackground : Colors.textPrimary
        border.color: light ? Colors.borderLight : "transparent"
    }

    FontMetrics { id: fontMetrics}
}
