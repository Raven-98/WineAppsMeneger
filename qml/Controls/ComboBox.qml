import QtQuick
import QtQuick.Controls.Basic

import Modules
import Controls

ComboBox {
    id: root

    implicitWidth: 100
    implicitHeight: 32
    leftPadding: !mirrored ? 12 : editable && activeFocus ? 3 : 1
    font.pixelSize: Helper.fontPixelSize
    opacity: enabled ? 1.0 : 0.3

    delegate: ItemDelegate {
        width: root.width
        implicitHeight: root.implicitHeight
        contentItem: Text {
            text: root.textRole ? (Array.isArray(root.model) ? modelData[root.textRole] : model[root.textRole]) : modelData
            font.pixelSize: root.font.pixelSize
            font.bold: root.highlightedIndex === index
            color: root.highlightedIndex === index ? Colors.selectionText : Colors.textInverted
            elide: Text.ElideRight
            verticalAlignment: Text.AlignVCenter
        }
        background: Rectangle {
            color: root.highlightedIndex === index ? Colors.buttonHover : "transparent"
        }
        highlighted: root.highlightedIndex === index
    }

    background: Rectangle {
        color: Colors.textfaildColor
        border.color: root.pressed || popup.visible || root.hovered ? Colors.accent : Colors.borderColor
        border.width: 2
    }

    indicator: Canvas {
        id: canvas
        x: root.width - width - root.rightPadding
        y: root.topPadding + (root.availableHeight - height) / 2
        width: 12
        height: 8
        contextType: "2d"

        Connections {
            target: root
            function onPressedChanged() { canvas.requestPaint(); }
        }

        onPaint: {
            context.reset();
            context.moveTo(0, 0);
            context.lineTo(width, 0);
            context.lineTo(width / 2, height);
            context.closePath();
            context.fillStyle = root.pressed || popup.visible ? Colors.panelAltBackground : Colors.borderColor;
            context.fill();
        }
    }

    contentItem: Text {
        leftPadding: 0
        rightPadding: root.indicator.width + root.spacing
        text: root.displayText
        font: root.font
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight

    }

    popup: Popup {
        id: popup
        y: root.height - 1
        width: root.width
        implicitHeight: contentItem.implicitHeight
        padding: 1

        contentItem: ListView {
            clip: true
            implicitHeight: contentHeight
            model: root.popup.visible ? root.delegateModel : null
            currentIndex: root.highlightedIndex
//            ScrollIndicator.vertical: CScrollIndicator {}
            ScrollBar.vertical: ScrollBar {}
        }

        background: Rectangle {
            color: Colors.textfaildColor
            border.color: Colors.panelAltBackground
            radius: 2
        }
    }
}
