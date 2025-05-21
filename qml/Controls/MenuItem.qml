import QtQuick
import QtQuick.Controls.Basic

import Modules

MenuItem {
    id: root

    property var menuParent: null

    onTextChanged: {
        if (menuParent) menuParent.changeWidth()
    }
    onHighlightedChanged: {
        if (root.subMenu)
            degArrow.requestPaint()
        if (menuParent) menuParent.hovered = highlighted
    }
    Component.onCompleted: {
        menuParent = (item => {
            var p = item.parent
            while (p) {
                if (p.isCustomMenu === true)
                    return p
                p = p.parent
            }
            return null
        })(root)
    }

    opacity: enabled ? 1.0 : 0.3
    contentItem: Row {
        spacing: root.spacing
        Image {
            anchors.verticalCenter: parent.verticalCenter
            height: (root.icon.source != "" ? Helper.iconSmallSize : 0)
            width: (root.icon.source != "" ? Helper.iconSmallSize : 0)
            source: root.icon.source
        }
        Text {
            anchors.verticalCenter: parent.verticalCenter
            text: root.text
            font.pixelSize: Helper.fontPixelSize
            font.bold: root.highlighted
            color: root.highlighted ? Colors.selectionText : Colors.textPrimary
        }
    }
    indicator: Item {
        x: !root.mirrored ? root.width - width
                                - root.rightPadding : root.leftPadding
        y: root.topPadding + (root.availableHeight - height) / 2
        width: root.parent.implHeight - 2
        height: root.parent.implHeight - 2
        Rectangle {
            width: 18
            height: 18
            anchors.centerIn: parent
            visible: root.checkable
            color: root.highlighted ? Colors.selectionText : Colors.textPrimary
            radius: 3
        }
        Rectangle {
            width: 16
            height: 16
            anchors.centerIn: parent
            visible: root.checkable
            color: "transparent"
            border.color: Colors.borderColor
            radius: 3
            Rectangle {
                width: 8
                height: 8
                anchors.centerIn: parent
                visible: root.checked
                color: Colors.panelAltBackground
                radius: 2
            }
        }
    }
    arrow: Canvas {
        id: degArrow
        x: root.mirrored ? root.leftPadding : root.width - width
                               - root.rightPadding
        y: root.topPadding + (root.availableHeight - height) / 2
        width: root.parent.implHeight - 2
        height: root.parent.implHeight - 2
        visible: root.subMenu
        onPaint: {
            var ctx = getContext("2d")
            let wh = Math.round(root.parent.implHeight * 1 / 3)
            ctx.fillStyle = root.highlighted ? Colors.selectionText : Colors.textPrimary
            ctx.moveTo(wh, wh)
            ctx.lineTo(width - wh, height / 2)
            ctx.lineTo(wh, height - wh)
            ctx.closePath()
            ctx.fill()
        }
    }
    background: Rectangle {
        anchors.fill: parent
        width: root.width
        height: root.height
        opacity: enabled ? 1 : 0.3
        color: root.highlighted ? Colors.buttonHover : "transparent"
    }
}
