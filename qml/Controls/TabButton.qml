import QtQuick
import QtQuick.Controls.Basic
import Modules

TabButton {
    id: root
    implicitWidth: Helper.buttWidth(buttText, fontMetrics, 100)
    implicitHeight: Math.max(32, buttText.implicitHeight)

    contentItem: Text {
        id: buttText
        text: root.text
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        font.pixelSize: Helper.fontPixelSize
        font.bold: root.down || root.hovered
        color: root.down ? Colors.selectionText : Colors.textPrimary
        opacity: enabled ? 1.0 : 0.3
    }

    background: Rectangle {
        id: backgroundRectangle
        color: root.active || root.down ? Colors.buttonPressed :  root.hovered || root.highlight  || root.checked ? Colors.buttonHover  : /*Colors.buttonBackground*/ "transparent"
        border.width: 1
        border.color: root.active || root.hovered || root.highlight ? Colors.borderHeavy  : Colors.borderColor
        opacity: enabled ? 1 : 0.3
    }
    FontMetrics { id: fontMetrics }
}
