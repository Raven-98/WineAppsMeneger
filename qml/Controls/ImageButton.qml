import QtQuick
import QtQuick.Controls
import Modules

Button {
    id: root

    property bool active: false
    property bool highlight: false

    antialiasing: true
    display: AbstractButton.TextUnderIcon
    width: parent.width
    implicitHeight: 32
    implicitWidth: 32
    contentItem: Image {
        id: contentImage
        source: root.icon.source
        fillMode: Image.PreserveAspectFit
        anchors.verticalCenter: parent.verticalCenter
        anchors.horizontalCenter: parent.horizontalCenter
        opacity: enabled ? 1 : 0.3
    }
    background: Rectangle {
        id: backgroundRectangle
        color: root.active
               || root.down ? Colors.buttonPressed :  root.hovered || root.highlight ? Colors.buttonHover  : Colors.buttonBackground
        border.width: 1
        border.color: root.active || root.hovered || root.highlight ? Colors.borderHeavy  : Colors.borderColor
        opacity: enabled ? 1 : 0.3
    }
}
